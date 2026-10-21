import fs from 'node:fs';
import path from 'node:path';

// The OS job owns the command before its first instruction, including detached descendants.
// All helper source is embedded here and therefore part of the static runner code digest.
const SCRIPT = String.raw`param([string]$InputFile, [string]$ReceiptFile)
$ErrorActionPreference = 'Stop'
try {
  Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
public class PortfolioJobReceipt {
  public int ExitCode;
  public bool TimedOut;
  public bool TerminationVerified;
}
public static class PortfolioOwnedJob {
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
  struct STARTUPINFO {
    public uint cb; public string reserved, desktop, title;
    public uint x,y,xsize,ysize,xchars,ychars,fill,flags;
    public ushort show,reservedSize; public IntPtr reservedBytes,input,output,error;
  }
  [StructLayout(LayoutKind.Sequential)]
  struct PROCESSINFO { public IntPtr process,thread; public uint pid,tid; }
  [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
  static extern IntPtr CreateJobObjectW(IntPtr attrs, string name);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool SetInformationJobObject(IntPtr job, int kind, IntPtr info, uint length);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool QueryInformationJobObject(IntPtr job, int kind, IntPtr info, uint length, out uint actual);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool TerminateJobObject(IntPtr job, uint code);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool TerminateProcess(IntPtr process, uint code);
  [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
  static extern bool CreateProcessW(string app, StringBuilder command, IntPtr pa, IntPtr ta, bool inherit,
    uint flags, IntPtr environment, string cwd, ref STARTUPINFO startup, out PROCESSINFO process);
  [DllImport("kernel32.dll", SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
  [DllImport("kernel32.dll", SetLastError=true)] static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
  [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr process, out uint code);
  [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int which);
  [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
  [DllImport("kernel32.dll")] static extern ulong GetTickCount64();
  static void Check(bool ok) { if (!ok) throw new InvalidOperationException("owned Windows job control failed"); }
  static string Quote(string value) {
    var result = new StringBuilder("\""); int slashes = 0;
    foreach (char ch in value) {
      if (ch == '\\') { slashes++; continue; }
      if (ch == '"') { result.Append('\\', slashes * 2 + 1); result.Append(ch); }
      else { result.Append('\\', slashes); result.Append(ch); }
      slashes = 0;
    }
    result.Append('\\', slashes * 2); result.Append('"'); return result.ToString();
  }
  static int Active(IntPtr job) {
    IntPtr info = Marshal.AllocHGlobal(48);
    try { uint count; Check(QueryInformationJobObject(job, 1, info, 48, out count)); return Marshal.ReadInt32(info, 40); }
    finally { Marshal.FreeHGlobal(info); }
  }
  public static PortfolioJobReceipt Run(string executable, string[] args, string cwd,
    IDictionary<string,string> variables, double timeoutMilliseconds, string cancelFile) {
    IntPtr job = IntPtr.Zero, block = IntPtr.Zero; PROCESSINFO process = new PROCESSINFO();
    bool assigned = false;
    try {
      if (File.Exists(cancelFile)) return new PortfolioJobReceipt { ExitCode=-1, TimedOut=true, TerminationVerified=true };
      job = CreateJobObjectW(IntPtr.Zero, null); Check(job != IntPtr.Zero);
      int size = IntPtr.Size == 8 ? 144 : 112;
      IntPtr limits = Marshal.AllocHGlobal(size);
      try {
        for (int i=0; i<size; i++) Marshal.WriteByte(limits,i,0);
        Marshal.WriteInt32(limits,16,0x2000); // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway permission
        Check(SetInformationJobObject(job,9,limits,(uint)size));
      } finally { Marshal.FreeHGlobal(limits); }
      var command = new StringBuilder(Quote(executable)); foreach (string arg in args) command.Append(" " + Quote(arg));
      var names = new List<string>(variables.Keys); names.Sort(StringComparer.OrdinalIgnoreCase);
      var environment = new StringBuilder(); foreach (string key in names) environment.Append(key+"="+variables[key]+"\0");
      environment.Append('\0'); block = Marshal.StringToHGlobalUni(environment.ToString());
      var startup = new STARTUPINFO(); startup.cb=(uint)Marshal.SizeOf(typeof(STARTUPINFO)); startup.flags=0x100;
      startup.input=GetStdHandle(-10); startup.output=GetStdHandle(-11); startup.error=GetStdHandle(-12);
      Check(CreateProcessW(executable,command,IntPtr.Zero,IntPtr.Zero,true,0x08000404,block,cwd,ref startup,out process));
      Check(AssignProcessToJobObject(job,process.process)); assigned=true;
      Check(ResumeThread(process.thread) != 0xffffffff);
      ulong start = GetTickCount64(); bool timeout=false;
      while (true) {
        uint wait = WaitForSingleObject(process.process,25);
        if (wait == 0) break;
        Check(wait == 258);
        if (File.Exists(cancelFile) || GetTickCount64()-start >= timeoutMilliseconds) { timeout=true; break; }
      }
      uint code = 0;
      if (!timeout) Check(GetExitCodeProcess(process.process,out code));
      Check(TerminateJobObject(job,timeout ? 124u : 0u)); // also stops children after a successful parent exit
      ulong verification = GetTickCount64();
      while (Active(job) != 0 && GetTickCount64()-verification < 5000) Thread.Sleep(10);
      return new PortfolioJobReceipt { ExitCode=timeout ? -1 : unchecked((int)code), TimedOut=timeout, TerminationVerified=Active(job)==0 };
    } finally {
      if (!assigned && process.process != IntPtr.Zero) TerminateProcess(process.process,125);
      if (job != IntPtr.Zero) CloseHandle(job);
      if (process.thread != IntPtr.Zero) CloseHandle(process.thread);
      if (process.process != IntPtr.Zero) CloseHandle(process.process);
      if (block != IntPtr.Zero) Marshal.FreeHGlobal(block);
    }
  }
}
'@
  $spec = Get-Content -LiteralPath $InputFile -Raw -Encoding UTF8 | ConvertFrom-Json
  $variables = New-Object 'System.Collections.Generic.Dictionary[string,string]'
  foreach ($property in $spec.environment.PSObject.Properties) { $variables.Add($property.Name,[string]$property.Value) }
  $receipt = [PortfolioOwnedJob]::Run([string]$spec.executable,[string[]]$spec.arguments,[string]$spec.cwd,$variables,[double]$spec.timeoutMilliseconds,[string]$spec.cancelFile)
  [IO.File]::WriteAllText($ReceiptFile,($receipt | ConvertTo-Json -Compress),(New-Object Text.UTF8Encoding($false)))
  if (-not $receipt.TerminationVerified) { exit 125 }
  if ($receipt.TimedOut) { exit 124 }
  exit $receipt.ExitCode
} catch {
  [Console]::Error.WriteLine('owned Windows job helper failed')
  exit 125
}
`;

export function windowsJobInvocation(executable, args, { cwd, env, timeoutSeconds }) {
  const parent = path.resolve(env.TEMP);
  if (fs.realpathSync(parent) !== parent || !fs.statSync(parent).isDirectory()) throw new Error('unsafe process-helper temporary directory');
  const root = fs.mkdtempSync(path.join(parent, 'owned-job-'));
  const script = path.join(root, 'job.ps1'), input = path.join(root, 'input.json'), receipt = path.join(root, 'receipt.json'), cancel = path.join(root, 'cancel');
  fs.writeFileSync(script, SCRIPT);
  fs.writeFileSync(input, JSON.stringify({ executable, arguments: args, cwd, environment: env, timeoutMilliseconds: timeoutSeconds * 1000, cancelFile: cancel }));
  return { executable: path.join(env.SYSTEMROOT, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe'),
    args: ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', script, '-InputFile', input, '-ReceiptFile', receipt], receipt, cancel,
    cleanup() {
      if (path.dirname(root) !== parent || fs.realpathSync(root) !== root || !path.basename(root).startsWith('owned-job-')) throw new Error('unsafe process-helper cleanup boundary');
      fs.rmSync(root, { recursive: true, force: true });
    } };
}
