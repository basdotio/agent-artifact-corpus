using System;
using System.IO;
using System.Diagnostics;
using System.Windows.Forms;

namespace ElectreeFi
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string venvPython = Path.Combine(baseDir, ".venv", "Scripts", "python.exe");
                string pythonExe = File.Exists(venvPython) ? venvPython : "python.exe";
                string appScript = Path.Combine(baseDir, "electreefi_app.py");

                if (!File.Exists(appScript))
                {
                    MessageBox.Show(
                        "Could not locate 'electreefi_app.py' in " + baseDir,
                        "ElectreeFi Studio Error",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = pythonExe;
                psi.Arguments = "\"" + appScript + "\"";
                psi.WorkingDirectory = baseDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                psi.WindowStyle = ProcessWindowStyle.Hidden;

                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Error launching ElectreeFi Studio:\n" + ex.Message,
                    "ElectreeFi Studio Launch Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }
    }
}
