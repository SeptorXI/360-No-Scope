package steven.armordisplays;

import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;

public final class ArmorDisplaysPlugin extends JavaPlugin {
    private static ComponentType<ChunkStore,DisplayBlock> displayType;
    private static ComponentType<EntityStore,VisualMarker> visualType;
    private static ArmorDisplaysPlugin instance;
    private static final Set<String> REPORTED = ConcurrentHashMap.newKeySet();
    public ArmorDisplaysPlugin(JavaPluginInit init) { super(init); }
    @Override protected void setup() {
        instance = this;
        displayType = getChunkStoreRegistry().registerComponent(DisplayBlock.class,"ADDisplay",DisplayBlock.CODEC);
        visualType = getEntityStoreRegistry().registerComponent(VisualMarker.class,()->new VisualMarker(null));
        getChunkStoreRegistry().registerSystem(new DisplaySystems.Lifecycle());
        getChunkStoreRegistry().registerSystem(new DisplaySystems.ContainerChange());
        getChunkStoreRegistry().registerSystem(new DisplaySystems.DisplayChange());
        getChunkStoreRegistry().registerSystem(new DisplaySystems.Refresh());
        getEntityStoreRegistry().registerSystem(new DisplaySystems.OrphanCleanup());
        getLogger().at(Level.INFO).log("Armor Displays registered: native saved containers, filtered equipment slots, transient visual props");
    }
    public static ComponentType<ChunkStore,DisplayBlock> displayComponentType() { return displayType; }
    public static ComponentType<EntityStore,VisualMarker> visualComponentType() { return visualType; }
    static void report(String detail,Throwable failure) {
        String message=detail+": "+failure;
        if(instance!=null && REPORTED.add(message)) instance.getLogger().at(Level.WARNING).log(message);
    }
}
