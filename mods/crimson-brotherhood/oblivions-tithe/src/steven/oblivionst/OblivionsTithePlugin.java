package steven.oblivionst;

import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.server.core.plugin.*;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.logging.Level;

public final class OblivionsTithePlugin extends JavaPlugin {
    public static final String ITEM_ID="Weapon_Daggers_Oblivions_Tithe";
    private static ComponentType<EntityStore,VenomState> venomType;
    public OblivionsTithePlugin(JavaPluginInit init){super(init);}
    @Override protected void setup(){
        venomType=getEntityStoreRegistry().registerComponent(VenomState.class,VenomState::new);
        getCodecRegistry(Interaction.CODEC).register("OTDaggerDamage",DaggerDamageInteraction.class,DaggerDamageInteraction.CODEC);
        getEntityStoreRegistry().registerSystem(new VenomCaptureSystem());
        getEntityStoreRegistry().registerSystem(new VenomHitSystem());
        getEntityStoreRegistry().registerSystem(new VenomTickSystem());
        getLogger().at(Level.INFO).log("Oblivion's Tithe registered: native reverse-grip Daggers; Daedric Venom 2 Poison/stack/sec, 10-stack target cap, six-second refresh.");
    }
    public static ComponentType<EntityStore,VenomState> venomComponentType(){
        if(venomType==null)throw new IllegalStateException("Oblivion's Tithe has not initialized");
        return venomType;
    }
    @Override protected void shutdown(){DaggerDamageInteraction.clearThreadContext();VenomHitSystem.clearPending();}
}
