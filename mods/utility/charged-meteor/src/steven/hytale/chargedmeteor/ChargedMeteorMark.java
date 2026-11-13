package steven.hytale.chargedmeteor;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.modules.projectile.component.ImpactModifiers;
import java.util.HashMap;

public final class ChargedMeteorMark extends SimpleInstantInteraction {
    public static final BuilderCodec<ChargedMeteorMark> CODEC = BuilderCodec.builder(
            ChargedMeteorMark.class, ChargedMeteorMark::new, SimpleInstantInteraction.CODEC)
            .build();

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        var metadata = context.getMetaStore();
        var cast = metadata.getIfPresentMetaObject(ImpactModifiers.CAST_SNAPSHOT);
        if (cast == null) {
            return;
        }

        // Keep support runes and Endgame cast bonuses while extending only this cast's Burn.
        var attributes = new HashMap<>(cast.getAttributes());
        attributes.put("Duration", cast.getAttribute("Duration", 4f) * 1.5f);
        metadata.putMetaObject(ImpactModifiers.CAST_SNAPSHOT,
                new ImpactModifiers(attributes, cast.getOnHitEffectIds(), cast.getElementalCauseId()));
    }
}
