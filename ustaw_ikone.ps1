# ustaw_ikone.ps1
$AppId = "RejestrUsterek.Desktop.App"
$ShortcutName = "Rejestr Usterek"

$desktops = @(
    [Environment]::GetFolderPath("Desktop"),
    [Environment]::GetFolderPath("CommonDesktopDirectory")
)

$lnkPath = $null
foreach ($d in $desktops) {
    $candidate = Join-Path $d "$ShortcutName.lnk"
    if (Test-Path $candidate) { $lnkPath = $candidate; break }
}

if (-not $lnkPath) {
    Write-Host "Nie znaleziono skrotu '$ShortcutName.lnk' na pulpicie." -ForegroundColor Red
    foreach ($d in $desktops) {
        Get-ChildItem $d -Filter "*.lnk" -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $($_.Name)" }
    }
    Read-Host "Enter aby zamknac"
    exit 1
}

Write-Host "Znaleziono skrot: $lnkPath" -ForegroundColor Cyan

Add-Type -AssemblyName System.Windows.Forms

$code = @"
using System;
using System.Runtime.InteropServices;

public class ShellLinkHelper {
    [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
    static extern int SHGetPropertyStoreFromParsingName(
        string pszPath, IntPtr pbc, int flags, ref Guid iid, out IPropertyStore ppv);

    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IPropertyStore {
        int GetCount(out uint c);
        int GetAt(uint i, out PropertyKey k);
        int GetValue(ref PropertyKey k, out PropVariant v);
        int SetValue(ref PropertyKey k, ref PropVariant v);
        int Commit();
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct PropertyKey {
        public Guid fmtid;
        public uint pid;
    }

    [StructLayout(LayoutKind.Explicit, Size = 16)]
    public struct PropVariant {
        [FieldOffset(0)] public ushort vt;
        [FieldOffset(8)] public IntPtr pszVal;
    }

    public static int SetAppId(string path, string appId) {
        Guid iid = new Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99");
        IPropertyStore store;
        int hr = SHGetPropertyStoreFromParsingName(path, IntPtr.Zero, 2, ref iid, out store);
        if (hr != 0) return hr;

        PropertyKey key = new PropertyKey();
        key.fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3");
        key.pid = 5;

        PropVariant pv = new PropVariant();
        pv.vt = 31; // VT_LPWSTR
        pv.pszVal = Marshal.StringToCoTaskMemUni(appId);

        hr = store.SetValue(ref key, ref pv);
        if (hr == 0) hr = store.Commit();
        Marshal.FreeCoTaskMem(pv.pszVal);
        Marshal.ReleaseComObject(store);
        return hr;
    }
}
"@

try {
    Add-Type -TypeDefinition $code
    $hr = [ShellLinkHelper]::SetAppId($lnkPath, $AppId)
    if ($hr -eq 0) {
        Write-Host "OK - AppUserModelID ustawione: $AppId" -ForegroundColor Green
        Write-Host ""
        Write-Host "Co dalej:"
        Write-Host "  1. Uruchom aplikacje przez .bat"
        Write-Host "  2. Prawy klik na ikone na pasku -> Przypnij do paska zadan"
        Write-Host "  3. Gotowe"
    } else {
        Write-Host ("Blad SetAppId HRESULT: 0x{0:X}" -f $hr) -ForegroundColor Red
    }
} catch {
    Write-Host "Blad: $_" -ForegroundColor Red
}

Read-Host "Nacisnij Enter aby zamknac"
