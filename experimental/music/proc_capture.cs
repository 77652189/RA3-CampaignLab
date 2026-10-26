// Record what one process (and its children) plays, nothing else: WASAPI process loopback (Windows 10 2004+).
//   proc_capture.exe <pid> <seconds> <out.wav>       44.1 kHz 16-bit stereo; silent stretches kept in place
// Built by listen.py with the .NET Framework csc.exe (C# 5), no packages.
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

[ComImport, Guid("72A22D78-CDE4-431D-B8CC-843A71199B6D"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IActivateAudioInterfaceAsyncOperation {
    void GetActivateResult(out int hr, [MarshalAs(UnmanagedType.IUnknown)] out object iface);
}

[ComImport, Guid("41D949AB-9862-444A-80F6-C261334DA5EB"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IActivateAudioInterfaceCompletionHandler {
    void ActivateCompleted(IActivateAudioInterfaceAsyncOperation op);
}

[ComImport, Guid("94ea2b94-e9cc-49e0-c0ff-ee64ca8f5b90"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAgileObject { }

[ComImport, Guid("1CB9AD4C-DBFA-4c32-B178-C2F568A703B2"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioClient {
    void Initialize(int shareMode, int streamFlags, long bufferDuration, long periodicity, IntPtr format, IntPtr sessionGuid);
    void GetBufferSize(out uint frames);
    void GetStreamLatency(out long latency);
    void GetCurrentPadding(out uint frames);
    void IsFormatSupported(int shareMode, IntPtr format, out IntPtr closest);
    void GetMixFormat(out IntPtr format);
    void GetDevicePeriod(out long def, out long min);
    void Start();
    void Stop();
    void Reset();
    void SetEventHandle(IntPtr handle);
    void GetService([MarshalAs(UnmanagedType.LPStruct)] Guid riid, [MarshalAs(UnmanagedType.IUnknown)] out object service);
}

[ComImport, Guid("C8ADBD64-E71E-48a0-A4DE-185C395CD317"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioCaptureClient {
    void GetBuffer(out IntPtr data, out uint frames, out uint flags, out ulong devicePosition, out ulong qpcPosition);
    void ReleaseBuffer(uint frames);
    void GetNextPacketSize(out uint frames);
}

class Handler : IActivateAudioInterfaceCompletionHandler, IAgileObject {
    public readonly ManualResetEvent Done = new ManualResetEvent(false);
    public object Client;
    public int Hr;
    public void ActivateCompleted(IActivateAudioInterfaceAsyncOperation op) {
        object c;
        op.GetActivateResult(out Hr, out c);
        Client = c;
        Done.Set();
    }
}

static class Program {
    [DllImport("Mmdevapi.dll", ExactSpelling = true, PreserveSig = false)]
    static extern void ActivateAudioInterfaceAsync([MarshalAs(UnmanagedType.LPWStr)] string path,
        [MarshalAs(UnmanagedType.LPStruct)] Guid riid, IntPtr activationParams,
        IActivateAudioInterfaceCompletionHandler handler, out IActivateAudioInterfaceAsyncOperation op);

    const int RATE = 44100, CH = 2, BYTES = 4;

    [MTAThread]
    static int Main(string[] args) {
        uint pid = uint.Parse(args[0]);
        double seconds = double.Parse(args[1], System.Globalization.CultureInfo.InvariantCulture);
        string outPath = args[2];

        IntPtr p = Marshal.AllocHGlobal(12);                   // AUDIOCLIENT_ACTIVATION_PARAMS
        Marshal.WriteInt32(p, 0, 1);                           // AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK
        Marshal.WriteInt32(p, 4, (int)pid);
        Marshal.WriteInt32(p, 8, 0);                           // PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE
        IntPtr pv = Marshal.AllocHGlobal(24);                  // PROPVARIANT, VT_BLOB
        for (int i = 0; i < 24; i += 4) Marshal.WriteInt32(pv, i, 0);
        Marshal.WriteInt16(pv, 0, 65);
        Marshal.WriteInt32(pv, 8, 12);
        Marshal.WriteIntPtr(pv, 16, p);

        Handler h = new Handler();
        IActivateAudioInterfaceAsyncOperation op;
        ActivateAudioInterfaceAsync("VAD\\Process_Loopback", typeof(IAudioClient).GUID, pv, h, out op);
        if (!h.Done.WaitOne(5000) || h.Hr != 0) { Console.Error.WriteLine("activate failed 0x" + h.Hr.ToString("x")); return 2; }
        IAudioClient client = (IAudioClient)h.Client;

        IntPtr fmt = Marshal.AllocHGlobal(18);                 // WAVEFORMATEX, PCM 16-bit stereo
        Marshal.WriteInt16(fmt, 0, 1); Marshal.WriteInt16(fmt, 2, CH); Marshal.WriteInt32(fmt, 4, RATE);
        Marshal.WriteInt32(fmt, 8, RATE * BYTES); Marshal.WriteInt16(fmt, 12, BYTES); Marshal.WriteInt16(fmt, 14, 16);
        Marshal.WriteInt16(fmt, 16, 0);
        // LOOPBACK | AUTOCONVERTPCM | SRC_DEFAULT_QUALITY
        client.Initialize(0, 0x00020000 | unchecked((int)0x80000000) | 0x08000000, 2000000, 0, fmt, IntPtr.Zero);
        object svc;
        client.GetService(typeof(IAudioCaptureClient).GUID, out svc);
        IAudioCaptureClient cap = (IAudioCaptureClient)svc;

        long want = (long)(seconds * RATE);
        MemoryStream pcm = new MemoryStream();
        DateTime t0 = DateTime.UtcNow;
        long got = 0;
        client.Start();
        byte[] buf = new byte[0];
        while (got < want) {
            Thread.Sleep(10);
            uint n;
            cap.GetNextPacketSize(out n);
            while (n > 0) {
                IntPtr data; uint frames, flags; ulong dp, qp;
                cap.GetBuffer(out data, out frames, out flags, out dp, out qp);
                int len = (int)frames * BYTES;
                if (buf.Length < len) buf = new byte[len];
                if ((flags & 2) != 0) Array.Clear(buf, 0, len); else Marshal.Copy(data, buf, 0, len);
                pcm.Write(buf, 0, len);
                got += frames;
                cap.ReleaseBuffer(frames);
                cap.GetNextPacketSize(out n);
            }
            // the process may send nothing while it is quiet: fill to wall-clock time (keep 0.2 s for late packets)
            long due = (long)((DateTime.UtcNow - t0).TotalSeconds * RATE) - RATE / 5;
            if (due > got) { byte[] z = new byte[(due - got) * BYTES]; pcm.Write(z, 0, z.Length); got = due; }
        }
        client.Stop();

        byte[] body = pcm.ToArray();
        using (BinaryWriter w = new BinaryWriter(File.Create(outPath))) {
            w.Write(new char[] { 'R', 'I', 'F', 'F' }); w.Write(36 + body.Length);
            w.Write(new char[] { 'W', 'A', 'V', 'E', 'f', 'm', 't', ' ' }); w.Write(16);
            w.Write((short)1); w.Write((short)CH); w.Write(RATE); w.Write(RATE * BYTES); w.Write((short)BYTES); w.Write((short)16);
            w.Write(new char[] { 'd', 'a', 't', 'a' }); w.Write(body.Length); w.Write(body);
        }
        Console.WriteLine("recorded " + (got / (double)RATE).ToString("0.0") + " s of pid " + pid + " -> " + outPath);
        return 0;
    }
}
