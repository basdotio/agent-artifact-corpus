"""Win32 process ownership. Create suspended, assign Job, then resume.

No subprocess private attributes, shell parsing, global process-name cleanup or
breakaway flags. A failed assignment kills the still-suspended child. Job handle
is non-inheritable; only stdin/stdout/stderr are inherited via HANDLE_LIST.
"""
import ctypes as c
from ctypes import wintypes as w
import os
import subprocess
import time
import threading
import io

SIZE = c.c_size_t
class Security(c.Structure):
    _fields_=[('length',w.DWORD),('descriptor',w.LPVOID),('inherit',w.BOOL)]
class Startup(c.Structure):
    _fields_=[('cb',w.DWORD),('reserved',w.LPWSTR),('desktop',w.LPWSTR),('title',w.LPWSTR),
              ('x',w.DWORD),('y',w.DWORD),('xSize',w.DWORD),('ySize',w.DWORD),
              ('xChars',w.DWORD),('yChars',w.DWORD),('fill',w.DWORD),('flags',w.DWORD),
              ('show',w.WORD),('reservedSize',w.WORD),('reservedBytes',w.LPVOID),
              ('stdin',w.HANDLE),('stdout',w.HANDLE),('stderr',w.HANDLE)]
class StartupEx(c.Structure):
    _fields_=[('info',Startup),('attributes',w.LPVOID)]
class ProcessInfo(c.Structure):
    _fields_=[('process',w.HANDLE),('thread',w.HANDLE),('pid',w.DWORD),('tid',w.DWORD)]
class BasicLimits(c.Structure):
    _fields_=[('processTime',c.c_int64),('jobTime',c.c_int64),('flags',w.DWORD),
              ('minWS',SIZE),('maxWS',SIZE),('activeLimit',w.DWORD),('affinity',SIZE),
              ('priority',w.DWORD),('scheduling',w.DWORD)]
class Counters(c.Structure):
    _fields_=[(n,c.c_uint64) for n in ('readOps','writeOps','otherOps','readBytes','writeBytes','otherBytes')]
class ExtendedLimits(c.Structure):
    _fields_=[('basic',BasicLimits),('io',Counters),('processMemory',SIZE),
              ('jobMemory',SIZE),('peakProcess',SIZE),('peakJob',SIZE)]
class Accounting(c.Structure):
    _fields_=[(n,c.c_int64) for n in ('user','kernel','periodUser','periodKernel')]+[
        (n,w.DWORD) for n in ('faults','total','active','terminated')]


def api():
    k=c.WinDLL('kernel32',use_last_error=True)
    signatures={
        'CloseHandle':([w.HANDLE],w.BOOL),
        'CreateJobObjectW':([w.LPVOID,w.LPCWSTR],w.HANDLE),
        'SetInformationJobObject':([w.HANDLE,c.c_int,w.LPVOID,w.DWORD],w.BOOL),
        'QueryInformationJobObject':([w.HANDLE,c.c_int,w.LPVOID,w.DWORD,w.LPVOID],w.BOOL),
        'AssignProcessToJobObject':([w.HANDLE,w.HANDLE],w.BOOL),
        'TerminateJobObject':([w.HANDLE,w.UINT],w.BOOL),
        'TerminateProcess':([w.HANDLE,w.UINT],w.BOOL),
        'CreatePipe':([c.POINTER(w.HANDLE),c.POINTER(w.HANDLE),c.POINTER(Security),w.DWORD],w.BOOL),
        'SetHandleInformation':([w.HANDLE,w.DWORD,w.DWORD],w.BOOL),
        'CreateFileW':([w.LPCWSTR,w.DWORD,w.DWORD,c.POINTER(Security),w.DWORD,w.DWORD,w.HANDLE],w.HANDLE),
        'InitializeProcThreadAttributeList':([w.LPVOID,w.DWORD,w.DWORD,c.POINTER(SIZE)],w.BOOL),
        'UpdateProcThreadAttribute':([w.LPVOID,w.DWORD,SIZE,w.LPVOID,SIZE,w.LPVOID,w.LPVOID],w.BOOL),
        'DeleteProcThreadAttributeList':([w.LPVOID],None),
        'CreateProcessW':([w.LPCWSTR,w.LPWSTR,w.LPVOID,w.LPVOID,w.BOOL,w.DWORD,w.LPVOID,w.LPCWSTR,c.POINTER(StartupEx),c.POINTER(ProcessInfo)],w.BOOL),
        'ResumeThread':([w.HANDLE],w.DWORD),
        'WaitForSingleObject':([w.HANDLE,w.DWORD],w.DWORD),
        'GetExitCodeProcess':([w.HANDLE,c.POINTER(w.DWORD)],w.BOOL),
    }
    for name,(args,ret) in signatures.items():
        call=getattr(k,name);call.argtypes=args;call.restype=ret
    return k


class OwnedProcess:
    def __init__(self, argv, cwd, env=None, interactive=False, text=False, capabilities=None):
        import msvcrt
        self.returncode=None; self.args=argv
        self.k=api(); k=self.k; self.job=None; self.handle=None
        self.stdin=self.stdout=self.stderr=None; handles=[]; attrs=None; attrs_ready=False; info=ProcessInfo()
        stage="initialization"
        def require(ok):
            if not ok:
                error=c.WinError(c.get_last_error())
                error.strerror=f"{stage}: {error.strerror}"
                raise error
        try:
            stage='CreateJobObjectW'
            self.job=k.CreateJobObjectW(None,None);require(self.job)
            stage='SetInformationJobObject'
            limits=ExtendedLimits();limits.basic.flags=0x2000 # KILL_ON_JOB_CLOSE
            require(k.SetInformationJobObject(self.job,9,c.byref(limits),c.sizeof(limits)))
            stage='CreatePipe'
            security=Security(c.sizeof(Security),None,True)
            pipes=[]
            for _ in range(2):
                read,write=w.HANDLE(),w.HANDLE()
                require(k.CreatePipe(c.byref(read),c.byref(write),c.byref(security),0))
                handles.extend([read.value,write.value]);require(k.SetHandleInformation(read,1,0))
                pipes.append((read.value,write.value))
            # AppContainer denies opening the DOS NUL device. An anonymous pipe
            # is a local kernel object already allowed by the same token. Closing
            # the parent writer gives noninteractive children immediate stdin EOF.
            stage='CreatePipe(stdin)'
            read,write=w.HANDLE(),w.HANDLE()
            require(k.CreatePipe(c.byref(read),c.byref(write),c.byref(security),0))
            handles.extend([read.value,write.value]);require(k.SetHandleInformation(write,1,0))
            input_pipe=(read.value,write.value)
            stage='process attributes'
            attribute_count=2 if capabilities is not None else 1
            size=SIZE();k.InitializeProcThreadAttributeList(None,attribute_count,0,c.byref(size))
            attrs=c.create_string_buffer(size.value)
            require(k.InitializeProcThreadAttributeList(attrs,attribute_count,0,c.byref(size)));attrs_ready=True
            inherited=(w.HANDLE*3)(input_pipe[0],pipes[0][1],pipes[1][1])
            require(k.UpdateProcThreadAttribute(attrs,0,0x20002,inherited,c.sizeof(inherited),None,None))
            if capabilities is not None:
                require(k.UpdateProcThreadAttribute(attrs,0,0x20009,c.byref(capabilities),c.sizeof(capabilities),None,None))
            startup=StartupEx();startup.info.cb=c.sizeof(startup);startup.attributes=c.cast(attrs,w.LPVOID)
            startup.info.flags=0x100;startup.info.stdin=input_pipe[0];startup.info.stdout=pipes[0][1];startup.info.stderr=pipes[1][1]
            environment=dict(os.environ if env is None else env)
            block=c.create_unicode_buffer('\0'.join(f'{key}={value}' for key,value in sorted(environment.items(),key=lambda p:p[0].upper()))+'\0\0')
            command=c.create_unicode_buffer(subprocess.list2cmdline(argv))
            stage='CreateProcessW'
            require(k.CreateProcessW(None,command,None,None,True,0x4|0x80000|0x400|0x08000000,block,str(cwd),c.byref(startup),c.byref(info)))
            self.handle=info.process;self.pid=info.pid
            stage='AssignProcessToJobObject'
            require(k.AssignProcessToJobObject(self.job,info.process))
            stage='ResumeThread'
            if k.ResumeThread(info.thread)==0xffffffff:raise c.WinError(c.get_last_error())
            if interactive:
                fd=msvcrt.open_osfhandle(input_pipe[1],os.O_WRONLY|os.O_BINARY);handles.remove(input_pipe[1])
                self.stdin=os.fdopen(fd,'wb',buffering=0)
            for name,(read,write) in zip(('stdout','stderr'),pipes):
                fd=msvcrt.open_osfhandle(read,os.O_RDONLY|os.O_BINARY);handles.remove(read)
                setattr(self,name,os.fdopen(fd,'rb',buffering=0))
            if text:
                for name in ('stdin','stdout','stderr'):
                    if getattr(self,name) is not None:setattr(self,name,io.TextIOWrapper(getattr(self,name),encoding='utf-8',write_through=True))
        except BaseException:
            if info.process:
                k.TerminateProcess(info.process,1);k.WaitForSingleObject(info.process,2000)
            self.close()
            raise
        finally:
            if info.thread:k.CloseHandle(info.thread)
            if attrs_ready:k.DeleteProcThreadAttributeList(attrs)
            for handle in handles:k.CloseHandle(handle)

    def poll(self):
        if self.returncode is not None:return self.returncode
        if self.k.WaitForSingleObject(self.handle,0)==258:return None
        code=w.DWORD()
        if not self.k.GetExitCodeProcess(self.handle,c.byref(code)):raise c.WinError(c.get_last_error())
        self.returncode=code.value
        return self.returncode

    def wait(self, timeout=None):
        result=self.k.WaitForSingleObject(self.handle,0xffffffff if timeout is None else max(0,int(timeout*1000)))
        if result==258:raise subprocess.TimeoutExpired('owned Windows process',timeout)
        if result!=0:raise c.WinError(c.get_last_error())
        return self.poll()

    def terminate(self):
        if not self.k.TerminateJobObject(self.job,1):raise c.WinError(c.get_last_error())
    kill=terminate

    def settle(self):
        self.terminate()
        deadline=time.monotonic()+2
        while True:
            value=Accounting()
            if not self.k.QueryInformationJobObject(self.job,1,c.byref(value),c.sizeof(value),None):return False
            if value.active==0:return True
            if time.monotonic()>=deadline:return False
            time.sleep(.02)

    def communicate(self, input=None, timeout=None):
        # Keep drainers across a timeout so callers can kill then collect output.
        if not hasattr(self,'_drainers'):
            self._output=[None,None]
            def read(index,stream):self._output[index]=stream.read()
            self._drainers=[threading.Thread(target=read,args=(i,stream),daemon=True) for i,stream in enumerate((self.stdout,self.stderr))]
            for thread in self._drainers:thread.start()
            if self.stdin:
                if input is not None:self.stdin.write(input);self.stdin.flush()
                self.stdin.close()
        deadline=None if timeout is None else time.monotonic()+timeout
        self.wait(timeout)
        for thread in self._drainers:
            thread.join(None if deadline is None else max(0,deadline-time.monotonic()))
        if any(t.is_alive() for t in self._drainers):raise subprocess.TimeoutExpired(self.args,timeout)
        return tuple(self._output)

    def close(self):
        for name in ('job','handle'):
            value=getattr(self,name,None)
            if value:self.k.CloseHandle(value);setattr(self,name,None)
