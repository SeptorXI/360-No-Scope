package steven.armordisplays;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hypixel.hytale.math.shape.Box;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.asset.common.CommonAsset;
import com.hypixel.hytale.server.core.asset.common.CommonAssetRegistry;
import com.hypixel.hytale.server.core.asset.type.item.config.Item;
import com.hypixel.hytale.server.core.asset.type.model.config.Model;
import com.hypixel.hytale.server.core.asset.type.model.config.ModelAttachment;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import org.joml.Matrix4d;
import org.joml.Quaterniond;
import org.joml.Vector3d;

/** Read-only model measurements normalize arbitrary mod weapon attachment roots. */
public final class ItemLayout {
    public record Placement(Model model, Rotation3f rotation, Vector3d center) {}
    private static final Map<String, CompletableFuture<Box>> CACHE = new ConcurrentHashMap<>();
    private ItemLayout() {}
    public static CompletableFuture<Box> bounds(String path) {
        return CACHE.computeIfAbsent(path, key -> {
            CommonAsset asset = CommonAssetRegistry.getByName(key);
            if (asset == null) return CompletableFuture.failedFuture(new IllegalArgumentException("Missing model: " + key));
            return asset.getBlob().thenApply(ItemLayout::measure);
        });
    }
    public static Placement placement(Item item, String kind) {
        if (item.getModel() == null || item.getTexture() == null)
            throw new IllegalArgumentException("Weapon has no display model/texture: " + item.getId());
        CompletableFuture<Box> pending = bounds(item.getModel());
        if (!pending.isDone()) return null;
        Box raw = pending.join();
        Rotation3f rotation = new Rotation3f();
        double width=raw.width(), height=raw.height(), depth=raw.depth();
        if (height >= width && height >= depth) rotation.setRoll((float)(-Math.PI/2));
        else if (depth >= width && depth >= height) rotation.setYaw((float)(Math.PI/2));
        Box aligned = raw.enclosingRotatedAABB(rotation.pitch(),rotation.yaw(),rotation.roll());
        double targetWidth = "Rack".equals(kind) ? 1.72 : 1.40;
        double targetHeight = "Rack".equals(kind) ? 0.48 : 0.58;
        double maxDimension = Math.max(aligned.width(), Math.max(aligned.height(), aligned.depth()));
        if (!Double.isFinite(maxDimension) || maxDimension <= 0) throw new IllegalArgumentException("Empty weapon model");
        double sourceScale = item.getScale() > 0 && Float.isFinite(item.getScale()) ? item.getScale() : 1;
        double fit = Math.min(1, Math.min(targetWidth/(aligned.width()*sourceScale),
            Math.min(targetHeight/(aligned.height()*sourceScale), 0.38/(aligned.depth()*sourceScale))));
        float scale = (float)(sourceScale*fit);
        Box scaled = new Box(raw).scale(scale);
        Model model = new Model("AD_Item_"+item.getId(), scale, Map.of(), new ModelAttachment[0], scaled,
            item.getModel(), item.getTexture(), null, null, 0,0,0,0, Map.of(), null,null,null,null,null,Map.of(),null,null);
        Vector3d center = new Vector3d(raw.middleX(),raw.middleY(),raw.middleZ()).mul(scale);
        rotation.transform(center);
        return new Placement(model, rotation, center);
    }
    /** Entity models use 64 pixels per world unit (block furniture uses 32). */
    public static Box measure(byte[] blob) {
        if (blob.length > 8_000_000) throw new IllegalArgumentException("Display model too large");
        JsonObject root = JsonParser.parseString(new String(blob,StandardCharsets.UTF_8)).getAsJsonObject();
        Box box = new Box().setEmpty();
        int[] count = {0};
        walk(root.getAsJsonArray("nodes"),new Matrix4d(),box,0,count);
        if (!box.min.isFinite() || !box.max.isFinite() || box.width()+box.height()+box.depth() <= 0)
            throw new IllegalArgumentException("Display model has no visible geometry");
        return box;
    }
    private static void walk(JsonArray nodes, Matrix4d parent, Box bounds, int depth, int[] count) {
        if (nodes == null) return;
        if (depth > 64) throw new IllegalArgumentException("Display model nesting limit");
        for (JsonElement element:nodes) {
            if (++count[0] > 20000) throw new IllegalArgumentException("Display model node limit");
            JsonObject node=element.getAsJsonObject();
            Vector3d p=vector(node.getAsJsonObject("position"),0).div(64);
            JsonObject r=node.getAsJsonObject("orientation");
            Quaterniond q=r==null?new Quaterniond():new Quaterniond(number(r,"x",0),number(r,"y",0),number(r,"z",0),number(r,"w",1)).normalize();
            Matrix4d transform=new Matrix4d(parent).translate(p).rotate(q);
            JsonObject shape=node.getAsJsonObject("shape");
            if (shape!=null && (!shape.has("visible") || shape.get("visible").getAsBoolean())) {
                String type=shape.has("type")?shape.get("type").getAsString():"none";
                if ("box".equals(type) || "quad".equals(type)) {
                    JsonObject settings=shape.getAsJsonObject("settings");
                    Vector3d size=vector(settings==null?null:settings.getAsJsonObject("size"),0);
                    if ("quad".equals(type) && settings!=null) {
                        String normal=settings.has("normal")?settings.get("normal").getAsString():"+Z";
                        if (normal.endsWith("X")) size.set(0,size.y,size.x);
                        else if (normal.endsWith("Y")) size.set(size.x,0,size.y);
                    }
                    size.mul(vector(shape.getAsJsonObject("stretch"),1)).div(128);
                    Vector3d offset=vector(shape.getAsJsonObject("offset"),0).div(64);
                    for(int x=-1;x<=1;x+=2)for(int y=-1;y<=1;y+=2)for(int z=-1;z<=1;z+=2) {
                        Vector3d corner=new Vector3d(size).mul(x,y,z).add(offset);
                        transform.transformPosition(corner);
                        bounds.min.min(corner);bounds.max.max(corner);
                    }
                }
            }
            walk(node.getAsJsonArray("children"),transform,bounds,depth+1,count);
        }
    }
    private static double number(JsonObject object,String name,double fallback) {
        return object!=null && object.has(name)?object.get(name).getAsDouble():fallback;
    }
    private static Vector3d vector(JsonObject object,double fallback) {
        return new Vector3d(number(object,"x",fallback),number(object,"y",fallback),number(object,"z",fallback));
    }
}
