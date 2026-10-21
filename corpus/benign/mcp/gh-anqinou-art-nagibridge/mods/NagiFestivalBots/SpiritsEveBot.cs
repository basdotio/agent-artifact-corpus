using System.Reflection;
using Microsoft.Xna.Framework;
using StardewValley;
using xTile.Dimensions;

namespace StardewValley.Minigames;

public sealed class SpiritsEveBot
{
    private static readonly BindingFlags Members = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
    private static readonly Vector2[] Waypoints =
    {
        new(23f, 29f),
        new(23f, 24f),
        new(20f, 24f),
        new(20f, 19f),
        new(15f, 19f),
        new(15f, 14f),
        new(10f, 14f),
        new(10f, 9f),
        new(8f, 9f),
        new(8f, 6f),
        new(6f, 6f)
    };

    private int waypointIndex;
    private double nextActionMs;

    public void Update(GameTime time)
    {
        if (!this.IsSpiritsEveActive())
        {
            this.Reset();
            return;
        }

        if (time.TotalGameTime.TotalMilliseconds < this.nextActionMs)
            return;

        if (this.waypointIndex < Waypoints.Length)
        {
            this.WarpTo(Waypoints[this.waypointIndex++]);
            this.nextActionMs = time.TotalGameTime.TotalMilliseconds + 250;
            return;
        }

        this.OpenGoldenPumpkinChest();
        this.nextActionMs = time.TotalGameTime.TotalMilliseconds + 1500;
    }

    private bool IsSpiritsEveActive()
    {
        return Game1.currentSeason.Equals("fall", StringComparison.OrdinalIgnoreCase) &&
            Game1.dayOfMonth == 27 &&
            Game1.currentLocation is not null &&
            ((bool?)typeof(Game1).GetMethod("isFestival", Members, null, Type.EmptyTypes, null)?.Invoke(null, null) ?? Game1.CurrentEvent is not null);
    }

    private void WarpTo(Vector2 tile)
    {
        Game1.player.currentLocation = Game1.currentLocation;
        Game1.player.Position = tile * Game1.tileSize;
    }

    private void OpenGoldenPumpkinChest()
    {
        foreach (Vector2 tile in this.FindActionTiles("GoldenPumpkin", "Chest", "Maze"))
        {
            Game1.currentLocation.checkAction(new Location((int)tile.X, (int)tile.Y), Game1.viewport, Game1.player);
            return;
        }

        Game1.currentLocation.checkAction(new Location(6, 6), Game1.viewport, Game1.player);
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

    private void Reset()
    {
        this.waypointIndex = 0;
        this.nextActionMs = 0;
    }
}
