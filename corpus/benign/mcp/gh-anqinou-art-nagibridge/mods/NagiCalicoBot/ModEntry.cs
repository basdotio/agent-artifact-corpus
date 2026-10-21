using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;
using StardewValley.Minigames;

namespace Nagi.CalicoBot;

public sealed class ModEntry : Mod
{
    private NagiCalicoBot? bot;

    public override void Entry(IModHelper helper)
    {
        this.bot = new NagiCalicoBot(this.Monitor);
        helper.Events.GameLoop.UpdateTicked += this.OnUpdateTicked;
    }

    private void OnUpdateTicked(object? sender, UpdateTickedEventArgs e)
    {
        if (this.bot is null || !Context.IsWorldReady)
            return;

        if (Game1.currentMinigame is CalicoJack calicoJack)
            this.bot.Update(calicoJack, e.Ticks);
        else
            this.bot.Reset();
    }
}
