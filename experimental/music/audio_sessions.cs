// List one process's audio sessions on every render device: device, state, volume, mute, peak level.
//   audio_sessions.exe <pid>                          list
//   audio_sessions.exe <pid> set <volume 0..1> <mute 0|1>   then set every one of them (Windows keeps a program's
//                                                     session volume and mute across runs: put back what you found)
using System;
using System.Runtime.InteropServices;

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorCo { }
[ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {
    int EnumAudioEndpoints(int flow, int mask, out IMMDeviceCollection c);
    int GetDefaultAudioEndpoint(int flow, int role, out IMMDevice d);
}
[ComImport, Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceCollection { int GetCount(out int n); int Item(int i, out IMMDevice d); }
[ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {
    int Activate(ref Guid iid, int ctx, IntPtr p, [MarshalAs(UnmanagedType.IUnknown)] out object o);
    int OpenPropertyStore(int access, out IPropertyStore s);
    int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
}
[ComImport, Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IPropertyStore { int GetCount(out int n); int GetAt(int i, out PropertyKey k); int GetValue(ref PropertyKey k, out PropVariant v); }
[StructLayout(LayoutKind.Sequential)] struct PropertyKey { public Guid fmtid; public int pid; }
[StructLayout(LayoutKind.Explicit)] struct PropVariant { [FieldOffset(0)] public short vt; [FieldOffset(8)] public IntPtr p; [FieldOffset(16)] public IntPtr q; }
[ComImport, Guid("77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioSessionManager2 {
    int GetAudioSessionControl(IntPtr a, int b, out IntPtr c); int GetSimpleAudioVolume(IntPtr a, int b, out IntPtr c);
    int GetSessionEnumerator(out IAudioSessionEnumerator e);
}
[ComImport, Guid("E2F5BB11-0570-40CA-ACDD-3AA01277DEE8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioSessionEnumerator { int GetCount(out int n); int GetSession(int i, out IAudioSessionControl2 s); }
[ComImport, Guid("bfb7ff88-7239-4fc9-8fa2-07c950be9c6d"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioSessionControl2 {
    int GetState(out int s); int GetDisplayName(out IntPtr n); int SetDisplayName(string n, ref Guid g);
    int GetIconPath(out IntPtr p); int SetIconPath(string p, ref Guid g); int GetGroupingParam(out Guid g); int SetGroupingParam(ref Guid g, ref Guid c);
    int RegisterAudioSessionNotification(IntPtr n); int UnregisterAudioSessionNotification(IntPtr n);
    int GetSessionIdentifier(out IntPtr s); int GetSessionInstanceIdentifier(out IntPtr s); int GetProcessId(out uint pid);
}
[ComImport, Guid("87CE5498-68D6-44E5-9215-6DA47EF883D8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface ISimpleAudioVolume { int SetMasterVolume(float v, ref Guid g); int GetMasterVolume(out float v); int SetMute(bool m, ref Guid g); int GetMute(out bool m); }
[ComImport, Guid("C02216F6-8C67-4B5B-9D00-D008E73E0064"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioMeterInformation { int GetPeakValue(out float v); }

static class Program {
    static string Name(IMMDevice d) {
        IPropertyStore s; d.OpenPropertyStore(0, out s);
        PropertyKey k = new PropertyKey(); k.fmtid = new Guid("a45c254e-df1c-4efd-8020-67d146a850e0"); k.pid = 14;
        PropVariant v; s.GetValue(ref k, out v);
        return v.vt == 31 ? Marshal.PtrToStringUni(v.p) : "?";
    }

    static int Main(string[] args) {
        uint pid = uint.Parse(args[0]);
        Guid iid = new Guid("77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F");
        IMMDeviceEnumerator en = (IMMDeviceEnumerator)new MMDeviceEnumeratorCo();
        IMMDevice def; en.GetDefaultAudioEndpoint(0, 1, out def); string defId; def.GetId(out defId);
        IMMDeviceCollection devs; en.EnumAudioEndpoints(0, 1, out devs);
        int nd; devs.GetCount(out nd);
        for (int d = 0; d < nd; d++) {
            IMMDevice dev; devs.Item(d, out dev); string id; dev.GetId(out id);
            object o; dev.Activate(ref iid, 23, IntPtr.Zero, out o);
            IAudioSessionEnumerator se; ((IAudioSessionManager2)o).GetSessionEnumerator(out se);
            int ns; se.GetCount(out ns);
            for (int s = 0; s < ns; s++) {
                IAudioSessionControl2 c; se.GetSession(s, out c); uint p; c.GetProcessId(out p);
                if (p != pid) continue;
                int st; c.GetState(out st);
                if (args.Length >= 4 && args[1] == "set") {
                    Guid none = Guid.Empty;
                    ((ISimpleAudioVolume)c).SetMasterVolume(float.Parse(args[2], System.Globalization.CultureInfo.InvariantCulture), ref none);
                    ((ISimpleAudioVolume)c).SetMute(args[3] == "1", ref none);
                }
                float vol; bool mute; ((ISimpleAudioVolume)c).GetMasterVolume(out vol); ((ISimpleAudioVolume)c).GetMute(out mute);
                float peak; ((IAudioMeterInformation)c).GetPeakValue(out peak);
                Console.WriteLine((id == defId ? "[default] " : "") + Name(dev) + " | state " + st + " (1 = active) | volume " + vol + " | mute " + mute + " | peak " + peak);
            }
        }
        return 0;
    }
}
