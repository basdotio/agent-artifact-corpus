using System.Reflection;
using Microsoft.Xna.Framework;
using StardewValley;
using StardewValley.Menus;
using xTile.Dimensions;

namespace StardewValley.Minigames;

public sealed class SpinningWheelBot
{
    private static readonly BindingFlags Members = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
    private double nextActionMs;

    public void Update(GameTime time)
    {
        if (!this.IsFairActive())
        {
            this.nextActionMs = 0;
            return;
        }

        if (time.TotalGameTime.TotalMilliseconds < this.nextActionMs)
            return;

        if (this.IsSpinningWheelOpen())
            this.BetMaxOnGreen();
        else
            this.OpenSpinningWheel();

        this.nextActionMs = time.TotalGameTime.TotalMilliseconds + 700;
    }

    private bool IsFairActive()
    {
        return Game1.currentSeason.Equals("fall", StringComparison.OrdinalIgnoreCase) &&
            Game1.dayOfMonth == 16 &&
            Game1.currentLocation is not null &&
            ((bool?)typeof(Game1).GetMethod("isFestival", Members, null, Type.EmptyTypes, null)?.Invoke(null, null) ?? Game1.CurrentEvent is not null);
    }

    private bool IsSpinningWheelOpen()
    {
        return Game1.activeClickableMenu?.GetType().Name.Contains("Wheel", StringComparison.OrdinalIgnoreCase) == true ||
            Game1.activeClickableMenu?.GetType().Name.Contains("Bet", StringComparison.OrdinalIgnoreCase) == true;
    }

    private void OpenSpinningWheel()
    {
        foreach (Vector2 tile in this.FindActionTiles("Wheel", "spin", "bet"))
        {
            Game1.player.Position = (tile + new Vector2(0f, 1f)) * Game1.tileSize;
            Game1.currentLocation.checkAction(new Location((int)tile.X, (int)tile.Y), Game1.viewport, Game1.player);
            return;
        }
    }

    private void BetMaxOnGreen()
    {
        object menu = Game1.activeClickableMenu!;
        int tokens = this.GetStarTokens();
        if (tokens <= 0)
            return;

        this.SetIntMember(menu, tokens, "currentBet", "bet", "amount", "amountBet", "betAmount");
        this.SetBoolMember(menu, true, "betOnGreen", "green", "isGreen", "greenSelected");
        if (this.InvokeFirst(menu, new[] { "setBet", "placeBet", "spin", "startSpin", "doneWithBet" }, tokens, true))
            return;

        foreach (ClickableComponent component in this.GetClickableComponents(menu))
        {
            string name = component.name ?? string.Empty;
            if (name.Contains("green", StringComparison.OrdinalIgnoreCase) || name.Contains("spin", StringComparison.OrdinalIgnoreCase) || name.Contains("done", StringComparison.OrdinalIgnoreCase))
                Game1.activeClickableMenu.receiveLeftClick(component.bounds.Center.X, component.bounds.Center.Y, playSound: true);
        }
    }

    private int GetStarTokens()
    {
        foreach (string name in new[] { "festivalScore", "starTokens", "currentFestivalScore" })
        {
            object? value = typeof(Game1).GetField(name, Members)?.GetValue(null) ?? typeof(Game1).GetProperty(name, Members)?.GetValue(null);
            if (value is int count)
                return count;
        }

        return Math.Max(0, Game1.player.Money);
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

    private bool SetIntMember(object target, int value, params string[] names)
    {
        foreach (string name in names)
        {
            FieldInfo? field = target.GetType().GetField(name, Members);
            if (field is not null && field.FieldType == typeof(int))
            {
                field.SetValue(target, value);
                return true;
            }

            PropertyInfo? property = target.GetType().GetProperty(name, Members);
            if (property is not null && property.PropertyType == typeof(int) && property.CanWrite)
            {
                property.SetValue(target, value);
                return true;
            }
        }

        return false;
    }

    private bool SetBoolMember(object target, bool value, params string[] names)
    {
        foreach (string name in names)
        {
            FieldInfo? field = target.GetType().GetField(name, Members);
            if (field is not null && field.FieldType == typeof(bool))
            {
                field.SetValue(target, value);
                return true;
            }
        }

        return false;
    }

    private bool InvokeFirst(object target, string[] methodNames, params object?[] args)
    {
        foreach (string name in methodNames)
        {
            MethodInfo? method = target.GetType().GetMethods(Members).FirstOrDefault(candidate => candidate.Name.Equals(name, StringComparison.OrdinalIgnoreCase));
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

    private IEnumerable<ClickableComponent> GetClickableComponents(object target)
    {
        foreach (FieldInfo field in target.GetType().GetFields(Members))
        {
            if (field.GetValue(target) is ClickableComponent component)
                yield return component;
            if (field.GetValue(target) is IEnumerable<ClickableComponent> components)
            {
                foreach (ClickableComponent nested in components)
                    yield return nested;
            }
        }
    }
}
