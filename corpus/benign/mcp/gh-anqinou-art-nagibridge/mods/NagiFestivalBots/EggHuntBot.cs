using System.Reflection;
using Microsoft.Xna.Framework;
using StardewValley;
using xTile.Dimensions;

namespace StardewValley.Minigames;

public sealed class EggHuntBot
{
    private static readonly BindingFlags Members = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
    private static readonly Vector2[] EggRoute =
    {
        new(26f, 57f),
        new(24f, 54f),
        new(21f, 51f),
        new(15f, 51f),
        new(13f, 54f),
        new(9f, 56f),
        new(9f, 49f),
        new(14f, 47f),
        new(17f, 43f),
        new(22f, 42f),
        new(25f, 46f),
        new(29f, 48f)
    };

    private int routeIndex;
    private double nextActionMs;

    public void Update(GameTime time)
    {
        if (!this.IsEggHuntActive())
        {
            this.Reset();
            return;
        }

        if (time.TotalGameTime.TotalMilliseconds < this.nextActionMs)
            return;

        if (this.routeIndex >= EggRoute.Length)
            return;

        Vector2 tile = EggRoute[this.routeIndex++];
        this.WarpTo(tile);
        this.CollectEgg(tile);
        this.nextActionMs = time.TotalGameTime.TotalMilliseconds + 250;
    }

    private bool IsEggHuntActive()
    {
        if (!Game1.currentSeason.Equals("spring", StringComparison.OrdinalIgnoreCase) || Game1.dayOfMonth != 13 || Game1.currentLocation is null)
            return false;

        Event? currentEvent = Game1.CurrentEvent;
        if (currentEvent is null)
            return false;

        if (this.ReadBool(currentEvent, "eggHuntStarted", "eggFestivalStarted", "raceActive", "timerStarted"))
            return true;

        int timer = this.ReadInt(currentEvent, "eggHuntTimer", "timer", "countdown");
        return timer > 0 || this.GetEventFestivalName(currentEvent).Contains("Egg", StringComparison.OrdinalIgnoreCase) && Game1.eventUp;
    }

    private void WarpTo(Vector2 tile)
    {
        Game1.player.currentLocation = Game1.currentLocation;
        Game1.player.Position = tile * Game1.tileSize;
    }

    private void CollectEgg(Vector2 tile)
    {
        Game1.currentLocation.checkAction(new Location((int)tile.X, (int)tile.Y), Game1.viewport, Game1.player);
        this.InvokeFirst(Game1.CurrentEvent, new[] { "checkForEgg", "collectEgg", "eggFestivalClick" }, (int)tile.X, (int)tile.Y);
    }

    private int ReadInt(object target, params string[] names)
    {
        foreach (string name in names)
        {
            object? value = target.GetType().GetField(name, Members)?.GetValue(target) ?? target.GetType().GetProperty(name, Members)?.GetValue(target);
            if (value is int result)
                return result;
        }

        return 0;
    }

    private bool ReadBool(object target, params string[] names)
    {
        foreach (string name in names)
        {
            object? value = target.GetType().GetField(name, Members)?.GetValue(target) ?? target.GetType().GetProperty(name, Members)?.GetValue(target);
            if (value is bool result)
                return result;
        }

        return false;
    }

    private bool InvokeFirst(object? target, string[] methodNames, params object?[] args)
    {
        if (target is null)
            return false;

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

    private string GetEventFestivalName(Event festivalEvent)
    {
        object? value = festivalEvent.GetType().GetField("FestivalName", Members)?.GetValue(festivalEvent) ??
            festivalEvent.GetType().GetProperty("FestivalName", Members)?.GetValue(festivalEvent) ??
            festivalEvent.GetType().GetField("festivalName", Members)?.GetValue(festivalEvent);
        return value as string ?? string.Empty;
    }

    private void Reset()
    {
        this.routeIndex = 0;
        this.nextActionMs = 0;
    }
}
