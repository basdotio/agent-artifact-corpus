using System.Reflection;
using Microsoft.Xna.Framework;
using StardewValley;
using StardewValley.Menus;
using xTile.Dimensions;
using SObject = StardewValley.Object;

namespace StardewValley.Minigames;

public sealed class GrangeDisplayBot
{
    private static readonly BindingFlags Members = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;

    private static readonly string[] CategoryNames =
    {
        "Animal", "Artisan", "Cooking", "Fish", "Forage", "Fruit", "Mineral", "Vegetable"
    };

    private int phase;
    private double nextActionMs;

    public void Update(GameTime time)
    {
        if (!this.IsFairActive())
        {
            this.Reset();
            return;
        }

        if (time.TotalGameTime.TotalMilliseconds < this.nextActionMs)
            return;

        switch (this.phase)
        {
            case 0:
                this.WarpToGrange();
                this.Delay(time, 500);
                this.phase = 1;
                break;
            case 1:
                this.InteractWithGrange();
                this.Delay(time, 800);
                this.phase = 2;
                break;
            case 2:
                if (this.TryPlaceItems())
                    this.phase = 3;
                else
                    this.Delay(time, 500);
                break;
            default:
                break;
        }
    }

    private bool IsFairActive()
    {
        return Game1.currentSeason.Equals("fall", StringComparison.OrdinalIgnoreCase) &&
            Game1.dayOfMonth == 16 &&
            Game1.currentLocation is not null &&
            ((bool?)typeof(Game1).GetMethod("isFestival", Members, null, Type.EmptyTypes, null)?.Invoke(null, null) ?? Game1.CurrentEvent is not null);
    }

    private void WarpToGrange()
    {
        Vector2 tile = this.FindGrangeTile();
        Game1.player.currentLocation = Game1.currentLocation;
        Game1.player.Position = (tile + new Vector2(0f, 1f)) * Game1.tileSize;
        Game1.player.faceDirection(0);
    }

    private Vector2 FindGrangeTile()
    {
        GameLocation location = Game1.currentLocation;
        for (int x = 0; x < location.Map.Layers[0].LayerWidth; x++)
        {
            for (int y = 0; y < location.Map.Layers[0].LayerHeight; y++)
            {
                string? action = location.doesTileHaveProperty(x, y, "Action", "Buildings");
                if (action is not null &&
                    (action.Contains("Grange", StringComparison.OrdinalIgnoreCase) ||
                     action.Contains("Display", StringComparison.OrdinalIgnoreCase)))
                    return new Vector2(x, y);
            }
        }

        return new Vector2(37f, 62f);
    }

    private void InteractWithGrange()
    {
        Vector2 tile = this.FindGrangeTile();
        Game1.currentLocation.checkAction(new Location((int)tile.X, (int)tile.Y), Game1.viewport, Game1.player);
        this.SelectDialogOption("yes", "set", "place", "display");
    }

    private bool TryPlaceItems()
    {
        IClickableMenu? menu = Game1.activeClickableMenu;
        if (menu is null)
            return false;

        List<Item> bestItems = this.PickBestNineItems();
        if (bestItems.Count == 0)
            return true;

        IList<Item?>? grangeItems = this.GetGrangeItems(menu);
        if (grangeItems is not null)
        {
            for (int i = 0; i < Math.Min(bestItems.Count, grangeItems.Count); i++)
            {
                grangeItems[i] = bestItems[i].getOne();
            }

            this.InvokeFirst(menu, new[] { "update", "updateGrangeDisplay", "arrangeGrangeDisplay" });
            return true;
        }

        foreach (Item item in bestItems)
        {
            this.SelectInventoryItem(item);
            foreach (ClickableComponent component in this.GetClickableComponents(menu))
            {
                string name = component.name ?? string.Empty;
                if (name.Contains("slot", StringComparison.OrdinalIgnoreCase) ||
                    name.Contains("grange", StringComparison.OrdinalIgnoreCase))
                {
                    menu.receiveLeftClick(component.bounds.Center.X, component.bounds.Center.Y, playSound: true);
                    break;
                }
            }
        }

        return true;
    }

    private List<Item> PickBestNineItems()
    {
        List<Item> candidates = Game1.player.Items
            .Where(item => item is SObject)
            .OrderByDescending(this.ScoreItem)
            .ToList();

        List<Item> selected = new();
        HashSet<int> coveredCategories = new();

        foreach (Item item in candidates)
        {
            if (selected.Count >= 9)
                break;

            int cat = this.GetGrangeCategory(item);
            if (cat >= 0 && !coveredCategories.Contains(cat))
            {
                selected.Add(item);
                coveredCategories.Add(cat);
            }
        }

        foreach (Item item in candidates)
        {
            if (selected.Count >= 9)
                break;
            if (!selected.Contains(item))
                selected.Add(item);
        }

        return selected;
    }

    private int ScoreItem(Item item)
    {
        int quality = item is SObject obj ? obj.Quality : 0;
        int price = item is SObject sobj ? sobj.Price : 0;
        int categoryBonus = this.GetGrangeCategory(item) >= 0 ? 5000 : 0;
        return categoryBonus + quality * 1000 + price;
    }

    private int GetGrangeCategory(Item item)
    {
        if (item is not SObject obj)
            return -1;

        int cat = obj.Category;
        string name = obj.Name ?? string.Empty;

        // Animal Products: eggs, milk, wool, duck feather, rabbit's foot
        if (cat == -5 || cat == -6 ||
            name.Contains("Egg", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Milk", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Wool", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Duck Feather", StringComparison.OrdinalIgnoreCase))
            return 0;

        // Artisan Goods
        if (cat == -26 ||
            name.Contains("Wine", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Cheese", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Jelly", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Juice", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Honey", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Pickle", StringComparison.OrdinalIgnoreCase))
            return 1;

        // Cooking
        if (cat == -7)
            return 2;

        // Fish
        if (cat == -4)
            return 3;

        // Foraging
        if (cat == -81 || cat == -80 || cat == -23 ||
            name.Contains("Leek", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Daffodil", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Dandelion", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Horseradish", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Morel", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Chanterelle", StringComparison.OrdinalIgnoreCase))
            return 4;

        // Fruit
        if (cat == -79)
            return 5;

        // Mineral
        if (cat == -2 || cat == -12 ||
            name.Contains("Diamond", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Ruby", StringComparison.OrdinalIgnoreCase) ||
            name.Contains("Emerald", StringComparison.OrdinalIgnoreCase))
            return 6;

        // Vegetable
        if (cat == -75)
            return 7;

        return -1;
    }

    private IList<Item?>? GetGrangeItems(IClickableMenu menu)
    {
        foreach (string fieldName in new[] { "grangeItems", "gpieces", "displayItems", "items" })
        {
            object? value = menu.GetType().GetField(fieldName, Members)?.GetValue(menu);
            if (value is IList<Item?> itemList)
                return itemList;
        }

        return null;
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
