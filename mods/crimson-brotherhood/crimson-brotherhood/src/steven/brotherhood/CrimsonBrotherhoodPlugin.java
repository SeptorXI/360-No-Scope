package steven.brotherhood;

import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.event.events.player.PlayerDisconnectEvent;
import java.util.logging.Level;

/** Both equipped use and per-piece affinity require a primary Assassin path. */
public final class CrimsonBrotherhoodPlugin extends JavaPlugin {
    private ArmorAffinitySystem affinity;
    private static ComponentType<EntityStore,ArmorReturnState> returnType;
    public CrimsonBrotherhoodPlugin(JavaPluginInit init) { super(init); }
    @Override protected void setup() {
        returnType=getEntityStoreRegistry().registerComponent(ArmorReturnState.class,"CB_ArmorReturn",ArmorReturnState.CODEC);
        affinity = new ArmorAffinitySystem(message->getLogger().at(Level.SEVERE).log(message));
        getEntityStoreRegistry().registerSystem(affinity);
        getEventRegistry().register(PlayerDisconnectEvent.class, event -> affinity.disconnect(event.getPlayerRef().getUuid()));
        getLogger().at(Level.INFO).log("Crimson Brotherhood registered: four native armor pieces; hard primary-Assassin equip restriction; persisted safe inventory returns; per-piece leased Endless Leveling attributes.");
    }
    public static ComponentType<EntityStore,ArmorReturnState> returnComponentType() {
        if(returnType==null)throw new IllegalStateException("Crimson Brotherhood return storage not registered");
        return returnType;
    }
    @Override protected void shutdown() { if (affinity != null) affinity.close(); }
}
