using System.Reflection;
using Microsoft.Xna.Framework;
using StardewValley;
using StardewValley.Menus;
using xTile.Dimensions;
using SObject = StardewValley.Object;

namespace StardewValley.Minigames;

public sealed class LuauBot
{
    private static readonly BindingFlags Members = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
    private int phase;
    private double nextActionMs;

    public void Update(GameTime time)
    {
        if (!this.IsLuauActive())
        {
            this.Reset();
            return;
        }

        if (time.TotalGameTime.TotalMilliseconds < this.nextActionMs)
            return;

        switch (this.phase)
        {
            case 0:
                this.WarpToSoupPot();
                this.Delay(time, 400);
                this.phase = 1;
                break;
            case 1:
                this.InteractWithSoupPot();
                this.Delay(time, 700);
                this.phase = 2;
                break;
            default:
                if (this.SelectBestSoupItem(out Item? item))
                    this.AddItemToSoup(item);
                this.SelectDialogOption("yes", "add", "put");
                this.Delay(time, 1500);
                this.phase = 3;
                break;
        }
    }

    private bool IsLuauActive()
    {
        return Game1.currentSeason.Equals("summer", StringComparison.OrdinalIgnoreCase) &&
            Game1.dayOfMonth == 11 &&
            Game1.currentLocation is not null &&
            ((bool?)typeof(Game1).GetMethod("isFestival", Members, null, Type.EmptyTypes, null)?.Invoke(null, null) ?? Game1.CurrentEvent is not null);
    }

    private void WarpToSoupPot()
    {
        Vector2 pot = this.FindSoupPotTile();
        Game1.player.currentLocation = Game1.currentLocation;
        Game1.player.Position = (pot + new Vector2(0f, 1f)) * Game1.tileSize;
        Game1.player.faceDirection(0);
    }

    private Vector2 FindSoupPotTile()
    {
        GameLocation location = Game1.currentLocation;
        for (int x = 0; x < location.Map.Layers[0].LayerWidth; x++)
        {
            for (int y = 0; y < location.Map.Layers[0].LayerHeight; y++)
            {
                string? action = location.doesTileHaveProperty(x, y, "Action", "Buildings");
                if (action?.Contains("soup", StringComparison.OrdinalIgnoreCase) == true ||
                    action?.Contains("luau", StringComparison.OrdinalIgnoreCase) == true)
                    return new Vector2(x, y);
            }
        }

        return new Vector2(57f, 22f);
    }

    private void InteractWithSoupPot()
    {
        Vector2 tile = this.FindSoupPotTile();
        Game1.currentLocation.checkAction(new Location((int)tile.X, (int)tile.Y), Game1.viewport, Game1.player);
    }

    private bool SelectBestSoupItem(out Item? item)
    {
        item = Game1.player.Items
            .Where(candidate => candidate is not null)
            .OrderByDescending(this.ScoreSoupItem)
            .FirstOrDefault();
        return item is not null;
    }

    private int ScoreSoupItem(Item item)
    {
        string name = item.Name ?? item.DisplayName ?? string.Empty;
        int quality = item is SObject obj ? obj.Quality : 0;

        if (name.Contains("Wine", StringComparison.OrdinalIgnoreCase) && quality >= SObject.highQuality)
            return quality >= SObject.bestQuality ? 10000 : 9000;
        if (name.Contains("Goat Cheese", StringComparison.OrdinalIgnoreCase) && quality >= SObject.highQuality)
            return 8000;
        if (quality >= SObject.highQuality)
            return 7000 + quality;
        return 1000 + Math.Max(item.Stack, 1);
    }

    private void AddItemToSoup(Item item)
    {
        this.SelectInventoryItem(item);
        this.InvokeFirst(Game1.CurrentEvent, new[] { "setUpPlayerControlSequence", "answerDialogue" }, item);
        this.SelectDialogOption("yes", "add", "put");
        if (item.Stack > 1)
            item.Stack--;
        else
            Game1.player.removeItemFromInventory(item);
    }

    private void SelectInventoryItem(Item item)
    {
        int index = Game1.player.Items.IndexOf(item);
        if (index >= 0)
            Game1.player.CurrentToolIndex = index;
    }

    private bool SelectDialogOption(params string[] preferredTokens)
    {
        if (Game1.activeClickableMenu is not DialogueBox dialog)
            return false;

        Response? choice = this.GetResponses(dialog).FirstOrDefault(response =>
            preferredTokens.Any(token => response.responseKey.Contains(token, StringComparison.OrdinalIgnoreCase) ||
                                         response.responseText.Contains(token, StringComparison.OrdinalIgnoreCase)));
        if (choice is null)
            return false;

        Game1.currentLocation?.answerDialogueAction(choice.responseKey, Array.Empty<string>());
        Game1.exitActiveMenu();
        return true;
    }

    private IReadOnlyList<Response> GetResponses(DialogueBox dialog)
    {
        foreach (string fieldName in new[] { "responses", "dialogueResponses" })
        {
            if (dialog.GetType().GetField(fieldName, Members)?.GetValue(dialog) is IEnumerable<Response> responses)
                return responses.ToList();
        }

        return Array.Empty<Response>();
    }

    private bool InvokeFirst(object? target, string[] methodNames, params object?[] args)
    {
        if (target is null)
            return false;

        foreach (string name in methodNames)
        {
            MethodInfo? method = target.GetType().GetMethods(Members).FirstOrDefault(candidate => candidate.Name == name);
            if (method is not null)
            {
                try
                {
                    ParameterInfo[] parameters = method.GetParameters();
                    method.Invoke(target, parameters.Length == 0 ? null : args.Take(parameters.Length).ToArray());
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

    private void Delay(GameTime time, double milliseconds)
    {
        this.nextActionMs = time.TotalGameTime.TotalMilliseconds + milliseconds;
    }

    private void Reset()
    {
        this.phase = 0;
        this.nextActionMs = 0;
    }
}
