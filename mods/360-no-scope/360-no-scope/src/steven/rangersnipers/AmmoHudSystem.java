package steven.rangersnipers;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.DelayedEntitySystem;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.protocol.packets.interface_.HudComponent;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.hud.CustomUIHud;
import com.hypixel.hytale.server.core.entity.entities.player.hud.HudManager;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.ui.builder.UICommandBuilder;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.logging.Level;

/** Displays authoritative chamber and reserve counts without writing weapon state. */
final class AmmoHudSystem extends DelayedEntitySystem<EntityStore> {
    static final String KEY = "Steven_360NoScope_Ammo";
    private static final String UI_PATH = "Hud/RangerSnipers/AmmoCounter.ui";
    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();
    private final AtomicBoolean warned = new AtomicBoolean();

    AmmoHudSystem() {
        super(0.1f);
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Query.and(Player.getComponentType(), PlayerRef.getComponentType());
    }

    @Override
    public boolean isParallel(int archetypeChunkSize, int taskCount) {
        return false;
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk,
                     Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        Player player = chunk.getComponent(index, Player.getComponentType());
        PlayerRef playerRef = chunk.getComponent(index, PlayerRef.getComponentType());
        if (player == null || playerRef == null || !playerRef.getPacketHandler().stillActive()) return;

        HudManager manager = player.getHudManager();
        try {
            if (player.isWaitingForClientReady() || !isVisible(manager)) {
                removeCounter(manager, playerRef);
                return;
            }

            var owner = chunk.getReferenceTo(index);
            ItemStack weapon = InventoryComponent.getItemInHand(buffer, owner);
            ChamberState.Profile profile = weapon == null || weapon.isEmpty()
                ? null : RangerSnipersPlugin.PROFILES.get(weapon.getItemId());
            if (profile == null) {
                removeCounter(manager, playerRef);
                return;
            }

            // Use the same combined view and linked round ID as CommitReload.
            var reserve = InventoryComponent.getCombined(buffer, owner, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
            updateCounter(manager, playerRef, weapon, profile, reserve);
        } catch (RuntimeException failure) {
            // A malformed stack or optional HUD failure must not interrupt world ticks.
            try {
                removeCounter(manager, playerRef);
            } catch (RuntimeException cleanupFailure) {
                failure.addSuppressed(cleanupFailure);
            }
            if (warned.compareAndSet(false, true)) {
                LOGGER.at(Level.WARNING).withCause(failure).log("360 No Scope could not update its ammo HUD");
            }
        }
    }

    static boolean isVisible(HudManager manager) {
        var components = manager.getVisibleHudComponents();
        return components.contains(HudComponent.AmmoIndicator) && components.contains(HudComponent.Hotbar);
    }

    static void updateCounter(HudManager manager, PlayerRef playerRef, ItemStack weapon,
                              ChamberState.Profile profile, ItemContainer reserve) {
        int loaded = ChamberState.read(weapon, profile).loaded();
        int rounds = ChamberTransactions.reserveCount(reserve, profile.ammoId());
        CustomUIHud current = manager.getCustomHud(KEY);
        if (current == null) {
            manager.addCustomHud(playerRef, new Counter(playerRef, loaded, profile.capacity(), rounds));
        } else if (current instanceof Counter counter) {
            if (counter.getPlayerRef() == playerRef) {
                counter.sync(loaded, profile.capacity(), rounds);
            } else {
                manager.addCustomHud(playerRef, new Counter(playerRef, loaded, profile.capacity(), rounds));
            }
        }
    }

    static void removeCounter(HudManager manager, PlayerRef playerRef) {
        if (manager.getCustomHud(KEY) instanceof Counter) manager.removeCustomHud(playerRef, KEY);
    }

    private static final class Counter extends CustomUIHud {
        private int loaded;
        private int capacity;
        private int reserve;

        Counter(PlayerRef playerRef, int loaded, int capacity, int reserve) {
            super(playerRef, KEY);
            this.loaded = loaded;
            this.capacity = capacity;
            this.reserve = reserve;
        }

        @Override
        protected void build(UICommandBuilder commands) {
            commands.append(UI_PATH);
            setMagazine(commands, loaded, capacity);
            setReserve(commands, reserve);
        }

        void sync(int loaded, int capacity, int reserve) {
            boolean magazineChanged = this.loaded != loaded || this.capacity != capacity;
            boolean reserveChanged = this.reserve != reserve;
            if (!magazineChanged && !reserveChanged) return;

            UICommandBuilder commands = new UICommandBuilder();
            if (magazineChanged) setMagazine(commands, loaded, capacity);
            if (reserveChanged) setReserve(commands, reserve);
            update(false, commands);
            this.loaded = loaded;
            this.capacity = capacity;
            this.reserve = reserve;
        }

        private static void setMagazine(UICommandBuilder commands, int loaded, int capacity) {
            commands.set("#Magazine.Text", loaded + " / " + capacity);
        }

        private static void setReserve(UICommandBuilder commands, int reserve) {
            commands.set("#Reserve.Text", "RESERVE " + reserve);
        }
    }
}
