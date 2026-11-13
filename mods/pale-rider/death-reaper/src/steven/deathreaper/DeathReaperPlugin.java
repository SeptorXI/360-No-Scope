package steven.deathreaper;

import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.event.events.player.PlayerDisconnectEvent;
import java.util.logging.Level;

public final class DeathReaperPlugin extends JavaPlugin {
    private ArmorAffinitySystem affinity;
    public DeathReaperPlugin(JavaPluginInit init) { super(init); }
    @Override protected void setup() {
        affinity = new ArmorAffinitySystem();
        getEntityStoreRegistry().registerSystem(affinity);
        getEventRegistry().register(PlayerDisconnectEvent.class, event -> affinity.disconnect(event.getPlayerRef().getUuid()));
        getLogger().at(Level.INFO).log("Death Reaper registered: four native armor pieces; per-piece primary Necromancer affinity uses leased native Endless Leveling attributes.");
    }
    @Override protected void shutdown() { if (affinity != null) affinity.close(); }
}
