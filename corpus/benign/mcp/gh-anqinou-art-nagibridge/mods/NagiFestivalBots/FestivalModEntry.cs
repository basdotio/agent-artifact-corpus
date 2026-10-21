using Microsoft.Xna.Framework;
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;

namespace StardewValley.Minigames;

public sealed class FestivalModEntry : Mod
{
    private readonly FlowerDanceBot flowerDanceBot = new();
    private readonly LuauBot luauBot = new();
    private readonly WinterStarBot winterStarBot = new();
    private readonly MermaidBot mermaidBot = new();
    private readonly SpiritsEveBot spiritsEveBot = new();
    private readonly SpinningWheelBot spinningWheelBot = new();
    private readonly EggHuntBot eggHuntBot = new();

    public override void Entry(IModHelper helper)
    {
        helper.Events.GameLoop.UpdateTicked += this.OnUpdateTicked;
    }

    private void OnUpdateTicked(object? sender, UpdateTickedEventArgs e)
    {
        if (!Context.IsWorldReady || Game1.player is null)
            return;

        GameTime time = Game1.currentGameTime;
        this.mermaidBot.Update(time);

        if (Game1.currentSeason.Equals("spring", StringComparison.OrdinalIgnoreCase))
        {
            if (Game1.dayOfMonth == 13)
                this.eggHuntBot.Update(time);
            else if (Game1.dayOfMonth == 24)
                this.flowerDanceBot.Update(time);
            return;
        }

        if (Game1.currentSeason.Equals("summer", StringComparison.OrdinalIgnoreCase) && Game1.dayOfMonth == 11)
        {
            this.luauBot.Update(time);
            return;
        }

        if (Game1.currentSeason.Equals("fall", StringComparison.OrdinalIgnoreCase))
        {
            if (Game1.dayOfMonth == 16)
                this.spinningWheelBot.Update(time);
            else if (Game1.dayOfMonth == 27)
                this.spiritsEveBot.Update(time);
            return;
        }

        if (Game1.currentSeason.Equals("winter", StringComparison.OrdinalIgnoreCase) && Game1.dayOfMonth == 25)
            this.winterStarBot.Update(time);
    }
}
