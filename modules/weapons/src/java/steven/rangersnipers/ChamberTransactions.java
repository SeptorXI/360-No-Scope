package steven.rangersnipers;

import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import java.util.*;

/** World-thread native inventory adapter; compare full items before native REPLACE. */
public final class ChamberTransactions {
    public record Token(String instanceId, int revision, int plannedTransfer) {
        public Token(String instanceId, int revision) { this(instanceId, revision, 0); }
    }
    public record ReloadResult(boolean committed, int transferred, ItemStack weapon) {}
    public record ShotResult(boolean committed, int consumed, ItemStack weapon, ItemStack refund) {}
    private record Debit(short slot, ItemStack before, ItemStack after) {}
    private ChamberTransactions() {}

    public static Token token(ItemStack weapon, ChamberState.Profile profile) {
        ChamberState.State state = ChamberState.read(weapon, profile);
        if (state.instanceId() == null) throw new IllegalStateException("Uninitialized receiver");
        return new Token(state.instanceId(), state.revision());
    }

    public static Token reloadToken(ItemStack weapon, ChamberState.Profile profile, int plannedTransfer) {
        ChamberState.State state = ChamberState.read(weapon, profile);
        if (state.instanceId() == null || plannedTransfer < 1 ||
            plannedTransfer > profile.capacity() - state.loaded())
            throw new IllegalArgumentException("Invalid planned reload transfer");
        return new Token(state.instanceId(), state.revision(), plannedTransfer);
    }

    public static boolean matches(ItemStack weapon, ChamberState.Profile profile, Token token) {
        if (token == null) return false;
        ChamberState.State state = ChamberState.read(weapon, profile);
        return Objects.equals(token.instanceId(), state.instanceId()) && token.revision() == state.revision();
    }

    public static int reserveCount(ItemContainer reserve, String ammoId) {
        int count = 0;
        for (short slot = 0; slot < reserve.getCapacity(); slot++) {
            ItemStack item = reserve.getItemStack(slot);
            if (item != null && !item.isEmpty() && item.getItemId().equals(ammoId))
                count = Math.addExact(count, item.getQuantity());
        }
        return count;
    }

    public static ReloadResult reload(ItemContainer held, short heldSlot, ItemContainer reserve,
                                      ChamberState.Profile profile, Token token) {
        ItemStack weapon = held.getItemStack(heldSlot);
        if (!matches(weapon, profile, token)) return new ReloadResult(false, 0, weapon);
        int needed = profile.capacity() - ChamberState.read(weapon, profile).loaded();
        int planned = token.plannedTransfer();
        if (planned < 1 || planned > needed) return new ReloadResult(false, 0, weapon);
        List<Debit> debits = new ArrayList<>();
        int remaining = planned;
        for (short slot = 0; slot < reserve.getCapacity() && remaining > 0; slot++) {
            ItemStack item = reserve.getItemStack(slot);
            if (item == null || item.isEmpty() || !item.getItemId().equals(profile.ammoId())) continue;
            int take = Math.min(remaining, item.getQuantity());
            debits.add(new Debit(slot, item, item.getQuantity() == take ? null : item.withQuantity(item.getQuantity() - take)));
            remaining -= take;
        }
        // The clip depicts this exact count. A reserve change cannot silently
        // turn a double insertion into a single insertion after it has played.
        if (remaining != 0) return new ReloadResult(false, 0, weapon);
        int transferred = planned;
        // Construct/validate all metadata before removing even one reserve item.
        ItemStack loaded = ChamberState.withLoaded(weapon, profile, ChamberState.read(weapon, profile).loaded() + transferred);
        List<Debit> applied = new ArrayList<>();
        for (Debit debit : debits) {
            if (!replaceExact(reserve, debit.slot(), debit.before(), debit.after())) {
                rollback(reserve, applied);
                return new ReloadResult(false, 0, weapon);
            }
            applied.add(debit);
        }
        if (!replaceExact(held, heldSlot, weapon, loaded)) {
            rollback(reserve, applied);
            return new ReloadResult(false, 0, weapon);
        }
        return new ReloadResult(true, transferred, loaded);
    }

    public static boolean replaceExact(ItemContainer container, short slot, ItemStack before, ItemStack after) {
        if (!Objects.equals(container.getItemStack(slot), before)) return false;
        return container.replaceItemStackInSlot(slot, before, after).succeeded();
    }

    /** The production shot transaction; a token cannot commit twice. */
    public static ShotResult fire(ItemContainer held, short slot, ChamberState.Profile profile,
                                  Token token, int cost, boolean eternalShot) {
        ItemStack weapon = held.getItemStack(slot);
        if (!matches(weapon, profile, token) || token.plannedTransfer() != 0 || cost < 1 || cost > profile.capacity() ||
            ChamberState.read(weapon, profile).loaded() < cost)
            return new ShotResult(false, 0, weapon, null);
        ItemStack after = ChamberState.consume(weapon, profile, cost);
        if (!replaceExact(held, slot, weapon, after)) return new ShotResult(false, 0, weapon, null);
        return new ShotResult(true, cost, after, eternalShot ? new ItemStack(profile.ammoId(), 1) : null);
    }

    private static void rollback(ItemContainer reserve, List<Debit> applied) {
        for (int i = applied.size() - 1; i >= 0; i--) {
            Debit debit = applied.get(i);
            if (!replaceExact(reserve, debit.slot(), debit.after(), debit.before()))
                throw new IllegalStateException("Concurrent inventory mutation prevented chamber transfer rollback");
        }
    }
}
