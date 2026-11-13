package steven.rangersnipers;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.projectile.ProjectileModule;
import com.hypixel.hytale.server.core.modules.projectile.component.ImpactModifiers;
import com.hypixel.hytale.server.core.modules.projectile.component.ProjectileLaunchContext;
import com.hypixel.hytale.server.core.modules.projectile.config.ProjectileConfig;
import org.joml.Vector3d;

import java.util.concurrent.ThreadLocalRandom;

/** One authoritative shell launch, one ammo payment, several physical pellets. */
public final class ScatterInteraction extends ServerProjectileInteraction {
    public static final BuilderCodec<ScatterInteraction> CODEC = BuilderCodec.builder(ScatterInteraction.class,
        ScatterInteraction::new, ServerProjectileInteraction.CODEC)
        .append(new KeyedCodec<>("Pellets", Codec.INTEGER), (o, v) -> o.pellets = v, o -> o.pellets).add()
        .append(new KeyedCodec<>("SpreadDegrees", Codec.DOUBLE), (o, v) -> o.spread = v, o -> o.spread).add()
        .append(new KeyedCodec<>("BodyDamage", Codec.DOUBLE), (o, v) -> o.body = v, o -> o.body).add()
        .append(new KeyedCodec<>("HeadDamage", Codec.DOUBLE), (o, v) -> o.head = v, o -> o.head).add()
        .append(new KeyedCodec<>("Range", Codec.DOUBLE), (o, v) -> o.range = v, o -> o.range).add().build();

    private int pellets;
    private double spread, body, head, range;

    @Override protected void launchProjectiles(InteractionType type, InteractionContext context, ProjectileConfig config,
                                               Transform look) {
        if (pellets < 1 || pellets > 12 || !Double.isFinite(spread) || spread < 0 || spread > 20) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        var commands = context.getCommandBuffer();
        var owner = context.getOwningEntity();
        var forward = new Vector3d(look.getDirection()).normalize();
        var vertical = Math.abs(forward.y) > .99 ? new Vector3d(1, 0, 0) : new Vector3d(0, 1, 0);
        var side = new Vector3d(forward).cross(vertical).normalize();
        var up = new Vector3d(side).cross(forward).normalize();
        var ledger = pellets > 1 ? new ShotgunLedger(pellets, Math.max(body, head)) : null;
        var modifiers = ImpactModifiers.collect(context, owner, commands);
        var launch = new ProjectileLaunchContext(type, true);
        Long seed = launchSeed(context);
        long lifetimeMillis = (long)((lifetimeSeconds() + (pellets > 1 ? .25 : 0)) * 1000);
        double cone = Math.tan(Math.toRadians(spread));
        for (int i = 0; i < pellets; i++) {
            double radius;
            double angle;
            if (pellets == 1) {
                radius = Math.sqrt(ThreadLocalRandom.current().nextDouble()) * cone;
                angle = ThreadLocalRandom.current().nextDouble() * Math.PI * 2;
            } else {
                // Golden-angle disc starts at its center and balances the remaining pellets.
                radius = Math.sqrt((double)i / (pellets - 1)) * cone;
                angle = i * 2.399963229728653;
            }
            var direction = new Vector3d(forward).fma(radius * Math.cos(angle), side)
                .fma(radius * Math.sin(angle), up).normalize();
            var projectile = ProjectileModule.get().spawnProjectile(null, seed, owner, commands, config,
                new Vector3d(look.getPosition()), direction, lifetimeMillis);
            var pellet = ledger == null ? null : new ScatterPellet(ledger, i, body, head, range);
            registerProjectile(commands, owner, projectile, modifiers, launch, pellet, i == 0);
        }
    }
}
