using System.Reflection;
using Microsoft.Xna.Framework;
using StardewValley;
using StardewValley.Menus;

namespace StardewValley.Minigames;

public sealed class WinterStarBot
{
    private static readonly BindingFlags Members = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
    private int phase;
    private double nextActionMs;

    public void Update(GameTime time)
    {
        if (!this.IsWinterStarActive())
        {
            this.Reset();
            return;
        }

        if (time.TotalGameTime.TotalMilliseconds < this.nextActionMs)
            return;

        NPC? recipient = this.GetSecretGiftRecipient();
        if (recipient is null)
            return;

        switch (this.phase)
        {
            case 0:
                this.WarpPlayerNear(recipient);
                this.Delay(time, 400);
                this.phase = 1;
                break;
            case 1:
                if (this.TryFindUniversallyLovedItem(out Item? gift))
                    this.GiveItem(recipient, gift);
                this.Delay(time, 900);
                this.phase = 2;
                break;
            default:
                this.SelectDialogOption("yes", "give");
                this.Delay(time, 1200);
                break;
        }
    }

    private bool IsWinterStarActive()
    {
        return Game1.currentSeason.Equals("winter", StringComparison.OrdinalIgnoreCase) &&
            Game1.dayOfMonth == 25 &&
            Game1.currentLocation is not null &&
            ((bool?)typeof(Game1).GetMethod("isFestival", Members, null, Type.EmptyTypes, null)?.Invoke(null, null) ?? Game1.CurrentEvent is not null);
    }

    private NPC? GetSecretGiftRecipient()
    {
        foreach (string fieldName in new[] { "winterStarRecipient", "secretGiftRecipient", "festivalGiftRecipient", "giftRecipient" })
        {
            object? value = typeof(Game1).GetField(fieldName, Members)?.GetValue(null) ??
                typeof(Game1).GetProperty(fieldName, Members)?.GetValue(null);

            if (value is NPC npc)
                return npc;
            if (value is string name)
                return Game1.getCharacterFromName(name);
        }

        string? mail = Game1.player.mailReceived.FirstOrDefault(entry => entry.StartsWith("winterStar_", StringComparison.OrdinalIgnoreCase));
        return mail is not null ? Game1.getCharacterFromName(mail["winterStar_".Length..]) : null;
    }

    private bool TryFindUniversallyLovedItem(out Item? item)
    {
        string[] universalLoves =
        {
            "Prismatic Shard",
            "Rabbit's Foot",
            "Golden Pumpkin",
            "Pearl",
            "Magic Rock Candy"
        };

        item = Game1.player.Items
            .Where(candidate => candidate is not null)
            .OrderByDescending(candidate => universalLoves.Any(name => candidate.Name.Equals(name, StringComparison.OrdinalIgnoreCase)) ? 10000 + candidate.Stack : candidate.salePrice())
            .FirstOrDefault(candidate => universalLoves.Any(name => candidate.Name.Equals(name, StringComparison.OrdinalIgnoreCase)));

        return item is not null;
    }

    private void WarpPlayerNear(NPC npc)
    {
        Game1.player.currentLocation = npc.currentLocation ?? Game1.currentLocation;
        Game1.player.Position = (npc.Tile + new Vector2(0f, 1f)) * Game1.tileSize;
        Game1.player.faceGeneralDirection(npc.Position);
    }

    private void GiveItem(NPC npc, Item item)
    {
        this.SelectInventoryItem(item);
        npc.checkAction(Game1.player, Game1.currentLocation);
        this.InvokeFirst(npc, new[] { "tryToReceiveActiveObject", "receiveGift" }, Game1.player, true, true);
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
