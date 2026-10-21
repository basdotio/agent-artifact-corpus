using System.Reflection;
using Microsoft.Xna.Framework;
using StardewValley;
using StardewValley.Menus;
using StardewValley.Monsters;

namespace StardewValley.Minigames;

public sealed class FlowerDanceBot
{
    private static readonly BindingFlags Members = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
    private readonly Dictionary<string, int> lastFriendship = new();
    private int phase;
    private double nextActionMs;
    private string? targetName;

    public void Update(GameTime time)
    {
        if (!this.IsFlowerDanceActive())
        {
            this.Reset();
            return;
        }

        if (time.TotalGameTime.TotalMilliseconds < this.nextActionMs)
            return;

        NPC? target = this.FindBestDancePartner();
        if (target is null)
            return;

        this.targetName = target.Name;
        switch (this.phase)
        {
            case 0:
                this.WarpPlayerNear(target);
                this.Delay(time, 500);
                this.phase = 1;
                break;
            case 1:
                this.InteractWithNpc(target);
                this.Delay(time, 800);
                this.phase = 2;
                break;
            default:
                if (this.SelectDialogOption("dance", "yes", "ask"))
                    this.phase = 3;
                this.Delay(time, 800);
                break;
        }
    }

    private bool IsFlowerDanceActive()
    {
        return this.IsFestivalActive("spring", 24) &&
            (this.GetEventFestivalName(Game1.CurrentEvent).Contains("Flower Dance", StringComparison.OrdinalIgnoreCase) ||
             Game1.currentLocation?.NameOrUniqueName.Contains("Temp", StringComparison.OrdinalIgnoreCase) == true);
    }

    private NPC? FindBestDancePartner()
    {
        Farmer player = Game1.player;
        NPC? best = null;
        int bestPoints = int.MinValue;

        foreach (NPC npc in Utility.getAllCharacters())
        {
            if (npc is Monster || npc.Name == player.spouse || npc.Name.Equals("Dwarf", StringComparison.OrdinalIgnoreCase))
                continue;

            string name = npc.Name;
            int points = player.friendshipData.TryGetValue(name, out Friendship friendship)
                ? friendship.Points
                : this.lastFriendship.GetValueOrDefault(name, 0);
            this.lastFriendship[name] = points;

            if (points > bestPoints && this.CanNpcDance(npc))
            {
                best = npc;
                bestPoints = points;
            }
        }

        return best;
    }

    private bool CanNpcDance(NPC npc)
    {
        string name = npc.Name;
        return !string.IsNullOrWhiteSpace(name) &&
            !name.Equals("Lewis", StringComparison.OrdinalIgnoreCase) &&
            !name.Equals("Marnie", StringComparison.OrdinalIgnoreCase) &&
            !name.Equals("Pierre", StringComparison.OrdinalIgnoreCase) &&
            !name.Equals("Caroline", StringComparison.OrdinalIgnoreCase) &&
            !name.Equals("Robin", StringComparison.OrdinalIgnoreCase) &&
            !name.Equals("Demetrius", StringComparison.OrdinalIgnoreCase) &&
            !name.Equals("Pam", StringComparison.OrdinalIgnoreCase) &&
            !name.Equals("Clint", StringComparison.OrdinalIgnoreCase) &&
            !name.Equals("Willy", StringComparison.OrdinalIgnoreCase) &&
            !name.Equals("Linus", StringComparison.OrdinalIgnoreCase) &&
            !name.Equals("Wizard", StringComparison.OrdinalIgnoreCase) &&
            !name.Equals("Sandy", StringComparison.OrdinalIgnoreCase) &&
            !name.Equals("Krobus", StringComparison.OrdinalIgnoreCase);
    }

    private bool IsFestivalActive(string season, int day)
    {
        return Game1.currentSeason.Equals(season, StringComparison.OrdinalIgnoreCase) &&
            Game1.dayOfMonth == day &&
            Game1.currentLocation is not null &&
            ((bool?)typeof(Game1).GetMethod("isFestival", Members, null, Type.EmptyTypes, null)?.Invoke(null, null) ?? Game1.CurrentEvent is not null);
    }

    private void WarpPlayerNear(NPC npc)
    {
        Vector2 tile = npc.Tile + new Vector2(0f, 1f);
        Farmer player = Game1.player;
        player.currentLocation = npc.currentLocation ?? Game1.currentLocation;
        player.Position = tile * Game1.tileSize;
        player.faceGeneralDirection(npc.Position);
    }

    private void InteractWithNpc(NPC npc)
    {
        npc.checkAction(Game1.player, Game1.currentLocation);
    }

    private string GetEventFestivalName(Event? festivalEvent)
    {
        if (festivalEvent is null)
            return string.Empty;

        object? value = festivalEvent.GetType().GetField("FestivalName", Members)?.GetValue(festivalEvent) ??
            festivalEvent.GetType().GetProperty("FestivalName", Members)?.GetValue(festivalEvent) ??
            festivalEvent.GetType().GetField("festivalName", Members)?.GetValue(festivalEvent);
        return value as string ?? string.Empty;
    }

    private bool SelectDialogOption(params string[] preferredTokens)
    {
        if (Game1.activeClickableMenu is not DialogueBox dialog)
            return false;

        IReadOnlyList<Response> responses = this.GetResponses(dialog);
        if (responses.Count == 0)
            return false;

        Response choice = responses.FirstOrDefault(response =>
            preferredTokens.Any(token => response.responseKey.Contains(token, StringComparison.OrdinalIgnoreCase) ||
                                         response.responseText.Contains(token, StringComparison.OrdinalIgnoreCase))) ?? responses[^1];

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

    private void Delay(GameTime time, double milliseconds)
    {
        this.nextActionMs = time.TotalGameTime.TotalMilliseconds + milliseconds;
    }

    private void Reset()
    {
        this.phase = 0;
        this.nextActionMs = 0;
        this.targetName = null;
    }
}
