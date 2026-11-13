package steven.blacktempest;

import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.event.events.player.PlayerDisconnectEvent;
import java.util.logging.Level;

/** Three new pieces require primary Mage. Existing ABTT Hands remains unrestricted, with independent Mage affinity. */
public final class BlackTempestPlugin extends JavaPlugin {
    private ArmorAffinitySystem affinity;
    private static ComponentType<EntityStore,ArmorReturnState> returnType;
    public BlackTempestPlugin(JavaPluginInit init) { super(init); }
    @Override protected void setup() {
        returnType=getEntityStoreRegistry().registerComponent(ArmorReturnState.class,"BT_ArmorReturn",ArmorReturnState.CODEC);
        affinity = new ArmorAffinitySystem(message->getLogger().at(Level.SEVERE).log(message));
        getEntityStoreRegistry().registerSystem(affinity);
        getEventRegistry().register(PlayerDisconnectEvent.class, event -> affinity.disconnect(event.getPlayerRef().getUuid()));
        getLogger().at(Level.INFO).log("Black Tempest registered: three primary-Mage armor pieces plus independent affinity on existing ABTT Hands; persisted safe returns; named leased native attributes.");
    }
    public static ComponentType<EntityStore,ArmorReturnState> returnComponentType() {
        if(returnType==null)throw new IllegalStateException("Black Tempest return storage not registered");
        return returnType;
    }
    @Override protected void shutdown() { if (affinity != null) affinity.close(); }
}
