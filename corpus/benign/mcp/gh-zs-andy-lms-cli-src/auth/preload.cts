import { contextBridge, ipcRenderer } from 'electron';
contextBridge.exposeInMainWorld('lms', {
  state: () => ipcRenderer.invoke('lms:state'),
  login: (profile: string, platform: string) => ipcRenderer.invoke('lms:login', profile, platform),
  cancelLogin: () => ipcRenderer.invoke('lms:cancel-login'),
  stopAutoLogin: () => ipcRenderer.invoke('lms:stop-auto'),
  setLoginOptions: (profile: string, platform: string, options: { rememberPassword: boolean; autoLogin: boolean }) => ipcRenderer.invoke('lms:login-options', profile, platform, options),
  onState: (callback: (state: unknown) => void) => { ipcRenderer.on('lms:update', (_e, state) => callback(state)); },
});
