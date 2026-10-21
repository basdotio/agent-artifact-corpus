using System.Collections;
using System.Reflection;
using Microsoft.Xna.Framework;
using StardewModdingAPI;
using StardewValley.Menus;
using StardewValley.Minigames;

namespace Nagi.CalicoBot;

internal sealed class NagiCalicoBot
{
    private static readonly BindingFlags InstanceMembers = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;

    private readonly IMonitor monitor;
    private ulong nextActionTick;
    private string? lastWarning;

    public NagiCalicoBot(IMonitor monitor)
    {
        this.monitor = monitor;
    }

    public void Reset()
    {
        this.nextActionTick = 0;
        this.lastWarning = null;
    }

    public void Update(CalicoJack game, ulong tick)
    {
        if (tick < this.nextActionTick)
            return;

        if (!this.TryReadPlayerHand(game, out int playerValue, out bool isSoft) ||
            !this.TryReadDealerVisibleCard(game, out int dealerVisibleCard))
        {
            this.WarnOnce("CalicoJack is active, but the bot couldn't read the hand fields. Field names may have changed in this Stardew Valley version.");
            this.nextActionTick = tick + 60;
            return;
        }

        bool shouldHit = playerValue <= 16 || playerValue == 17 && isSoft;
        bool acted = shouldHit
            ? this.InvokeAction(game, new[] { "hit", "hitButton", "HitButton" }, "Hit", "hitMe", "doHit", "pressHit", "clickHit")
            : this.InvokeAction(game, new[] { "stand", "standButton", "StandButton" }, "Stand", "stay", "doStand", "pressStand", "clickStand");

        if (acted)
        {
            this.monitor.Log(
                $"{(shouldHit ? "Hit" : "Stand")} at player={playerValue}{(isSoft ? " soft" : "")}, dealer showing={dealerVisibleCard}.",
                LogLevel.Trace);
            this.nextActionTick = tick + 20;
        }
        else
        {
            this.WarnOnce("CalicoJack is active, but the bot couldn't invoke Hit/Stand. Method or button field names may have changed.");
            this.nextActionTick = tick + 60;
        }
    }

    private bool TryReadPlayerHand(CalicoJack game, out int value, out bool isSoft)
    {
        value = 0;
        isSoft = false;

        if (this.TryReadIntField(game, out value, "playerHandValue", "playerValue", "playerTotal", "playerHandTotal", "handValue", "currentPlayerTotal"))
        {
            isSoft = this.TryReadBoolField(game, "playerHasSoftAce", "playerSoft", "isSoft", "soft17") ||
                this.TryCalculateHandFromFields(game, out int calculatedValue, out bool calculatedSoft, "playerCards", "playerHand", "cards", "playerCardValues") &&
                calculatedValue == value &&
                calculatedSoft;
            return true;
        }

        return this.TryCalculateHandFromFields(game, out value, out isSoft, "playerCards", "playerHand", "cards", "playerCardValues");
    }

    private bool TryReadDealerVisibleCard(CalicoJack game, out int value)
    {
        if (this.TryReadIntField(game, out value, "dealerVisibleCard", "dealerShowing", "dealerUpCard", "dealerCard", "dealerFirstCard"))
            return true;

        value = 0;
        foreach (string fieldName in new[] { "dealerCards", "dealerHand", "dealerCardValues" })
        {
            if (this.TryGetFieldValue(game, fieldName, out object? fieldValue) && this.TryGetFirstCardValue(fieldValue, out value))
                return true;
        }

        return false;
    }

    private bool InvokeAction(CalicoJack game, string[] buttonFieldNames, params string[] methodNames)
    {
        Type type = game.GetType();
        foreach (string methodName in methodNames)
        {
            MethodInfo? method = type.GetMethod(methodName, InstanceMembers, binder: null, Type.EmptyTypes, modifiers: null);
            if (method is not null)
            {
                method.Invoke(game, null);
                return true;
            }
        }

        foreach (string buttonFieldName in buttonFieldNames)
        {
            if (this.TryGetFieldValue(game, buttonFieldName, out object? button) && button is ClickableComponent clickable)
            {
                game.receiveLeftClick(clickable.bounds.Center.X, clickable.bounds.Center.Y, playSound: true);
                return true;
            }
        }

        return false;
    }

    private bool TryCalculateHandFromFields(CalicoJack game, out int value, out bool isSoft, params string[] fieldNames)
    {
        value = 0;
        isSoft = false;

        foreach (string fieldName in fieldNames)
        {
            if (!this.TryGetFieldValue(game, fieldName, out object? fieldValue) || !this.TryReadCardValues(fieldValue, out List<int> cards))
                continue;

            value = this.CalculateBlackjackValue(cards, out isSoft);
            return cards.Count > 0;
        }

        return false;
    }

    private bool TryReadCardValues(object? source, out List<int> values)
    {
        values = new List<int>();

        if (source is null || source is string)
            return false;

        if (this.TryReadCardValue(source, out int singleValue))
        {
            values.Add(singleValue);
            return true;
        }

        if (source is IEnumerable enumerable)
        {
            foreach (object? item in enumerable)
            {
                if (this.TryReadCardValue(item, out int cardValue))
                    values.Add(cardValue);
            }
        }

        return values.Count > 0;
    }

    private bool TryReadCardValue(object? card, out int value)
    {
        value = 0;
        if (card is null)
            return false;

        if (card is int intValue)
        {
            value = this.NormalizeCardValue(intValue);
            return true;
        }

        Type type = card.GetType();
        foreach (string memberName in new[] { "value", "Value", "cardValue", "CardValue", "number", "Number", "rank", "Rank" })
        {
            FieldInfo? field = type.GetField(memberName, InstanceMembers);
            if (field is not null && TryConvertToInt(field.GetValue(card), out value))
            {
                value = this.NormalizeCardValue(value);
                return true;
            }

            PropertyInfo? property = type.GetProperty(memberName, InstanceMembers);
            if (property is not null && TryConvertToInt(property.GetValue(card), out value))
            {
                value = this.NormalizeCardValue(value);
                return true;
            }
        }

        return false;
    }

    private bool TryGetFirstCardValue(object? source, out int value)
    {
        value = 0;
        return this.TryReadCardValues(source, out List<int> cards) && cards.Count > 0 && (value = cards[0]) > 0;
    }

    private int CalculateBlackjackValue(IReadOnlyList<int> cards, out bool isSoft)
    {
        int total = 0;
        int aces = 0;

        foreach (int card in cards)
        {
            if (card == 1)
                aces++;

            total += card == 1 ? 11 : Math.Min(card, 10);
        }

        while (total > 21 && aces > 0)
        {
            total -= 10;
            aces--;
        }

        isSoft = aces > 0;
        return total;
    }

    private int NormalizeCardValue(int value)
    {
        return value > 10 ? 10 : Math.Max(value, 1);
    }

    private bool TryReadIntField(object instance, out int value, params string[] fieldNames)
    {
        foreach (string fieldName in fieldNames)
        {
            if (this.TryGetFieldValue(instance, fieldName, out object? fieldValue) && TryConvertToInt(fieldValue, out value))
                return true;
        }

        value = 0;
        return false;
    }

    private bool TryReadBoolField(object instance, params string[] fieldNames)
    {
        foreach (string fieldName in fieldNames)
        {
            if (this.TryGetFieldValue(instance, fieldName, out object? fieldValue) && fieldValue is bool value)
                return value;
        }

        return false;
    }

    private bool TryGetFieldValue(object instance, string fieldName, out object? value)
    {
        FieldInfo? field = instance.GetType().GetField(fieldName, InstanceMembers);
        value = field?.GetValue(instance);
        return field is not null;
    }

    private static bool TryConvertToInt(object? value, out int result)
    {
        switch (value)
        {
            case int intValue:
                result = intValue;
                return true;
            case byte byteValue:
                result = byteValue;
                return true;
            case short shortValue:
                result = shortValue;
                return true;
            case long longValue when longValue is >= int.MinValue and <= int.MaxValue:
                result = (int)longValue;
                return true;
            default:
                result = 0;
                return false;
        }
    }

    private void WarnOnce(string message)
    {
        if (this.lastWarning == message)
            return;

        this.lastWarning = message;
        this.monitor.Log(message, LogLevel.Warn);
    }
}
