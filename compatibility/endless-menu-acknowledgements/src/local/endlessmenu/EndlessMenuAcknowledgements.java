package local.endlessmenu;

import com.hypixel.hytale.server.core.io.adapter.PacketAdapters;
import com.hypixel.hytale.server.core.io.adapter.PacketFilter;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.logging.Level;

/** Local compatibility helper. The original server and vendor archives remain untouched. */
public final class EndlessMenuAcknowledgements extends JavaPlugin {
    private static final String INVENTORY = "com.airijko.endlessleveling.ui.InventoryUIPage";
    private static final String CLASS_SHA256 = "AB00FAE19907D6AE4ABF46CAB41A2ED241C29468E7E455B04A400FAEC1A8ADE1";
    private PacketFilter registration;

    public EndlessMenuAcknowledgements(JavaPluginInit init) { super(init); }

    @Override
    protected void setup() {
        try {
            Class<?> inventory = Class.forName(INVENTORY, false, getClass().getClassLoader());
            byte[] bytes;
            try (InputStream input = inventory.getResourceAsStream("InventoryUIPage.class")) {
                if (input == null) throw new IllegalStateException("Reviewed inventory class resource is unavailable");
                bytes = input.readAllBytes();
            }
            String actual = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
            if (!CLASS_SHA256.equalsIgnoreCase(actual)) {
                getLogger().at(Level.WARNING).log("Endless menu acknowledgement helper inactive: inventory class differs from reviewed Endless Leveling 14.5.6.");
                return;
            }
            var watcher = new TooltipAcknowledgementWatcher(message -> getLogger().at(Level.WARNING).log(message));
            registration = PacketAdapters.registerOutbound(watcher);
            getLogger().at(Level.INFO).log("Endless menu acknowledgement helper active: reviewed tooltip close watcher registered and counter field resolved.");
        } catch (Exception | LinkageError failure) {
            getLogger().at(Level.WARNING).log("Endless menu acknowledgement helper inactive: required compatibility checks failed (%s).", failure.getClass().getSimpleName());
        }
    }

    @Override
    protected void shutdown() {
        if (registration != null) {
            PacketAdapters.deregisterOutbound(registration);
            registration = null;
        }
    }
}
