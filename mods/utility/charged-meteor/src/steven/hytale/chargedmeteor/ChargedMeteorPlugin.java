package steven.hytale.chargedmeteor;

import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.time.Instant;
import org.joml.Vector3d;

public final class ChargedMeteorPlugin extends JavaPlugin {
    static ComponentType<EntityStore, MeteorContact> contactType;
    static ComponentType<EntityStore, MeteorLighting> lightingType;

    public ChargedMeteorPlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        contactType = getEntityStoreRegistry().registerComponent(MeteorContact.class,
                () -> new MeteorContact(Instant.MAX));
        getEntityStoreRegistry().registerSystem(new MeteorContact.ContactSystem(contactType));
        lightingType = getEntityStoreRegistry().registerComponent(MeteorLighting.class,
                () -> new MeteorLighting(new Vector3d(), Instant.EPOCH));
        getEntityStoreRegistry().registerSystem(new MeteorLighting.LightingSystem(lightingType));
        getCodecRegistry(Interaction.CODEC)
                .register("ChargedMeteorLivingTarget", LivingTargetInteraction.class, LivingTargetInteraction.CODEC)
                .register("ChargedMeteorMark", ChargedMeteorMark.class, ChargedMeteorMark.CODEC)
                .register("ChargedMeteorAim", AimedMeteorInteraction.class, AimedMeteorInteraction.CODEC)
                .register("ChargedMeteorImpact", MeteorImpactInteraction.class, MeteorImpactInteraction.CODEC);
    }
}
