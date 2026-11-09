package steven.rangersnipers;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.WieldingInteraction;

/** Native held aiming without the inherited shield/progress HUD indicator.
 *
 * Wielding inherits ChargingInteraction.ABSTRACT_CODEC, not its concrete codec,
 * so a DisplayProgress JSON field does not change the transmitted flag. Keep
 * the native Wielding packet and behavior while setting that field in code.
 */
public final class AimInteraction extends WieldingInteraction {
    public static final BuilderCodec<AimInteraction> CODEC = BuilderCodec
        .builder(AimInteraction.class, AimInteraction::new, WieldingInteraction.CODEC)
        .build();

    public AimInteraction() {
        displayProgress = false;
    }
}
