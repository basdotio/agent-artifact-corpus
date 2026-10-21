using System.Reflection;
using Microsoft.Xna.Framework;
using StardewValley;

namespace StardewValley.Minigames;

public sealed class MermaidBot
{
    private static readonly BindingFlags Members = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
    private static readonly int[] ShellOrder = { 1, 5, 4, 2, 3 };
    private int index;
    private double nextActionMs;

    public void Update(GameTime time)
    {
        if (!this.IsMermaidShowActive())
        {
            this.Reset();
            return;
        }

        if (this.index >= ShellOrder.Length || time.TotalGameTime.TotalMilliseconds < this.nextActionMs)
            return;

        this.ClickShell(ShellOrder[this.index]);
        this.index++;
        this.nextActionMs = time.TotalGameTime.TotalMilliseconds + 450;
    }

    private bool IsMermaidShowActive()
    {
        if (!Game1.currentSeason.Equals("winter", StringComparison.OrdinalIgnoreCase) || Game1.dayOfMonth is < 15 or > 17)
            return false;

        object? minigame = Game1.currentMinigame;
        if (minigame?.GetType().Name.Contains("Mermaid", StringComparison.OrdinalIgnoreCase) == true)
            return true;

        string locationName = Game1.currentLocation?.NameOrUniqueName ?? string.Empty;
        return locationName.Contains("Mermaid", StringComparison.OrdinalIgnoreCase) ||
            locationName.Contains("Submarine", StringComparison.OrdinalIgnoreCase) ||
            this.HasFieldValue(Game1.currentLocation, "mermaid", true);
    }

    private void ClickShell(int shellNumber)
    {
        object? show = (object?)Game1.currentMinigame ?? Game1.currentLocation;
        if (this.InvokeShellMethod(show, shellNumber))
            return;

        Rectangle bounds = this.GetShellBounds(shellNumber);
        Game1.currentMinigame?.receiveLeftClick(bounds.Center.X, bounds.Center.Y, playSound: true);
        Game1.currentLocation?.GetType().GetMethod("receiveLeftClick", Members)
            ?.Invoke(Game1.currentLocation, new object[] { bounds.Center.X + Game1.viewport.X, bounds.Center.Y + Game1.viewport.Y, true });
    }

    private bool InvokeShellMethod(object? target, int shellNumber)
    {
        if (target is null)
            return false;

        foreach (string name in new[] { "shellClicked", "clickShell", "pressShell", "doShellClick" })
        {
            MethodInfo? method = target.GetType().GetMethods(Members).FirstOrDefault(candidate => candidate.Name.Equals(name, StringComparison.OrdinalIgnoreCase));
            if (method is null)
                continue;

            ParameterInfo[] parameters = method.GetParameters();
            try
            {
                method.Invoke(target, parameters.Length == 0 ? null : new object[] { shellNumber - 1 }.Take(parameters.Length).ToArray());
                return true;
            }
            catch
            {
                continue;
            }
        }

        return false;
    }

    private Rectangle GetShellBounds(int shellNumber)
    {
        object? show = (object?)Game1.currentMinigame ?? Game1.currentLocation;
        foreach (string fieldName in new[] { "shells", "shellButtons", "shellComponents" })
        {
            object? value = show?.GetType().GetField(fieldName, Members)?.GetValue(show);
            if (value is System.Collections.IList list && list.Count >= shellNumber)
            {
                object? shell = list[shellNumber - 1];
                if (shell?.GetType().GetProperty("bounds", Members)?.GetValue(shell) is Rectangle bounds)
                    return bounds;
                if (shell?.GetType().GetField("bounds", Members)?.GetValue(shell) is Rectangle fieldBounds)
                    return fieldBounds;
            }
        }

        int width = Game1.viewport.Width;
        int y = Game1.viewport.Height / 2 + 160;
        int x = width / 2 - 256 + (shellNumber - 1) * 128;
        return new Rectangle(x, y, 64, 64);
    }

    private bool HasFieldValue(object? target, string token, bool expected)
    {
        if (target is null)
            return false;

        foreach (FieldInfo field in target.GetType().GetFields(Members))
        {
            if (field.Name.Contains(token, StringComparison.OrdinalIgnoreCase) && field.GetValue(target) is bool value && value == expected)
                return true;
        }

        return false;
    }

    private void Reset()
    {
        this.index = 0;
        this.nextActionMs = 0;
    }
}
