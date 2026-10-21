using System.Reflection;
using Microsoft.Xna.Framework;
using StardewValley;
using StardewValley.Menus;
using xTile.Dimensions;

namespace StardewValley.Minigames;

public sealed class StrengthGameBot
{
    private static readonly BindingFlags Members = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
    private double nextActionMs;
    private bool hasPlayed;

    public void Update(GameTime time)
    {
        if (!this.IsFairActive())
        {
            this.Reset();
            return;
        }

        if (time.TotalGameTime.TotalMilliseconds < this.nextActionMs)
            return;

        if (this.IsStrengthGameOpen())
            this.HitAtPeak();
        else if (!this.hasPlayed)
            this.OpenStrengthGame();

        this.nextActionMs = time.TotalGameTime.TotalMilliseconds + 500;
    }

    private bool IsFairActive()
    {
        return Game1.currentSeason.Equals("fall", StringComparison.OrdinalIgnoreCase) &&
            Game1.dayOfMonth == 16 &&
            Game1.currentLocation is not null &&
            ((bool?)typeof(Game1).GetMethod("isFestival", Members, null, Type.EmptyTypes, null)?.Invoke(null, null) ?? Game1.CurrentEvent is not null);
    }

    private bool IsStrengthGameOpen()
    {
        IClickableMenu? menu = Game1.activeClickableMenu;
        if (menu is null)
            return false;

        string typeName = menu.GetType().Name;
        return typeName.Contains("Strength", StringComparison.OrdinalIgnoreCase) ||
               typeName.Contains("Hammer", StringComparison.OrdinalIgnoreCase) ||
               typeName.Contains("SmashIt", StringComparison.OrdinalIgnoreCase);
    }

    private void OpenStrengthGame()
    {
        foreach (Vector2 tile in this.FindActionTiles("Strength", "Hammer", "Smash"))
        {
            Game1.player.Position = (tile + new Vector2(0f, 1f)) * Game1.tileSize;
            Game1.player.faceDirection(0);
            Game1.currentLocation.checkAction(new Location((int)tile.X, (int)tile.Y), Game1.viewport, Game1.player);
            return;
        }

        this.SelectDialogOption("yes", "play", "try", "strength", "hammer");
    }

    private void HitAtPeak()
    {
        IClickableMenu menu = Game1.activeClickableMenu!;

        float power = this.ReadFloat(menu, "power", "currentPower", "strength", "barPosition", "hitPower");
        bool rising = this.ReadBool(menu, "rising", "goingUp", "increasing");

        if (power > 0.9f || (power > 0.8f && !rising))
        {
            this.ClickCenter(menu);
            this.InvokeFirst(menu, new[] { "hit", "smash", "swing", "receiveLeftClick" });
            this.hasPlayed = true;
            return;
        }

        if (power <= 0f)
        {
            this.ClickCenter(menu);
        }
    }

    private void ClickCenter(IClickableMenu menu)
    {
        int cx = menu.xPositionOnScreen + menu.width / 2;
        int cy = menu.yPositionOnScreen + menu.height / 2;
        menu.receiveLeftClick(cx, cy, playSound: true);
    }

    private float ReadFloat(object target, params string[] names)
    {
        foreach (string name in names)
        {
            object? value = target.GetType().GetField(name, Members)?.GetValue(target) ??
                            target.GetType().GetProperty(name, Members)?.GetValue(target);
            if (value is float f)
                return f;
            if (value is double d)
                return (float)d;
            if (value is int i)
                return i / 100f;
        }

        return 0f;
    }

    private bool ReadBool(object target, params string[] names)
    {
        foreach (string name in names)
        {
            object? value = target.GetType().GetField(name, Members)?.GetValue(target) ??
                            target.GetType().GetProperty(name, Members)?.GetValue(target);
            if (value is bool b)
                return b;
        }

        return false;
    }

    private IEnumerable<Vector2> FindActionTiles(params string[] tokens)
    {
        GameLocation location = Game1.currentLocation;
        for (int x = 0; x < location.Map.Layers[0].LayerWidth; x++)
        {
            for (int y = 0; y < location.Map.Layers[0].LayerHeight; y++)
            {
                string? action = location.doesTileHaveProperty(x, y, "Action", "Buildings");
                if (action is not null && tokens.Any(token => action.Contains(token, StringComparison.OrdinalIgnoreCase)))
                    yield return new Vector2(x, y);
            }
        }
    }

    private bool SelectDialogOption(params string[] preferredTokens)
    {
        if (Game1.activeClickableMenu is not DialogueBox dialog)
            return false;

        foreach (string fieldName in new[] { "responses", "dialogueResponses" })
        {
            if (dialog.GetType().GetField(fieldName, Members)?.GetValue(dialog) is IEnumerable<Response> responses)
            {
                Response? choice = responses.FirstOrDefault(r =>
                    preferredTokens.Any(t => r.responseKey.Contains(t, StringComparison.OrdinalIgnoreCase) ||
                                              r.responseText.Contains(t, StringComparison.OrdinalIgnoreCase)));
                if (choice is not null)
                {
                    Game1.currentLocation?.answerDialogueAction(choice.responseKey, Array.Empty<string>());
                    Game1.exitActiveMenu();
                    return true;
                }
            }
        }

        return false;
    }

    private bool InvokeFirst(object target, string[] methodNames, params object?[] args)
    {
        foreach (string name in methodNames)
        {
            MethodInfo? method = target.GetType().GetMethods(Members).FirstOrDefault(m => m.Name.Equals(name, StringComparison.OrdinalIgnoreCase));
            if (method is not null)
            {
                try
                {
                    method.Invoke(target, args.Take(method.GetParameters().Length).ToArray());
                    return true;
                }
                catch
                {
                    continue;
                }
            }
        }

        return false;
    }

    private void Reset()
    {
        this.hasPlayed = false;
        this.nextActionMs = 0;
    }
}
