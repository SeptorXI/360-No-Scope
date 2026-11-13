package steven.rangersnipers;

import com.hypixel.hytale.codec.*;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.protocol.*;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.*;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.modules.projectile.component.ImpactModifiers;
import java.util.*;

/** Supplies a scalar to the unchanged native DamageEntity body/head pipeline. */
public final class FalloffInteraction extends SimpleInstantInteraction {
    public static final String ATTRIBUTE = "RS_DistanceDamage";
    public static final BuilderCodec<FalloffInteraction> CODEC = BuilderCodec.builder(FalloffInteraction.class,
        FalloffInteraction::new, SimpleInstantInteraction.CODEC)
        .append(new KeyedCodec<>("WeaponId", Codec.STRING), (o,v)->o.weaponId=v, o->o.weaponId).add().build();
    private String weaponId;
    public FalloffInteraction() {}
    @Override public WaitForDataFrom getWaitForDataFrom() { return WaitForDataFrom.Server; }
    @Override protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        // SimpleInstantInteraction otherwise calls firstRun here. NPC/local
        // simulation must never consume the authoritative impact claim or
        // rewrite its snapshot. The base simulateTick0 mirrors server failure
        // and applies the matching native success/failure operation branch.
    }
    @Override protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        try {
            var buffer = context.getCommandBuffer();
            var projectile = context.getEntity();
            if (buffer == null || projectile == null || !projectile.isValid()) { fail(context); return; }
            var flight = buffer.getComponent(projectile, RangerSnipersPlugin.flightType);
            var contact = context.getMetaStore().getIfPresentMetaObject(Interaction.HIT_LOCATION);
            if (flight == null || contact == null || !flight.profile().weaponId().equals(weaponId)) { fail(context); return; }
            float multiplier = (float) flight.profile().multiplier(flight.distanceForValidatedContact(contact));
            if (!flight.claimImpact()) { fail(context); return; }
            var original = ImpactModifiers.resolve(context, projectile, buffer);
            context.getMetaStore().putMetaObject(ImpactModifiers.CAST_SNAPSHOT, withMultiplier(original, multiplier));
        } catch (RuntimeException failure) {
            RangerSnipersPlugin.reportFailure(weaponId, failure);
            fail(context);
        }
    }
    /** Preserves other native support attributes, elemental cause, and hit effects. */
    public static ImpactModifiers withMultiplier(ImpactModifiers original, float multiplier) {
        if (!Float.isFinite(multiplier) || multiplier <= 0 || multiplier > 1)
            throw new IllegalArgumentException("Invalid sniper damage multiplier");
        Map<String, Float> attributes = new HashMap<>();
        if (original != null && original.getAttributes() != null) attributes.putAll(original.getAttributes());
        attributes.put(ATTRIBUTE, multiplier); // assign once; never multiply a previous falloff scalar
        return new ImpactModifiers(attributes, original == null ? null : original.getOnHitEffectIds(),
            original == null ? null : original.getElementalCauseId());
    }
    private static void fail(InteractionContext context) { context.getState().state = InteractionState.Failed; }
}
