import java.io.InputStream;
import java.lang.classfile.AccessFlags;
import java.lang.classfile.ClassFile;
import java.lang.classfile.ClassModel;
import java.lang.classfile.ClassTransform;
import java.lang.classfile.CodeBuilder;
import java.lang.classfile.CodeElement;
import java.lang.classfile.CodeTransform;
import java.lang.classfile.FieldModel;
import java.lang.classfile.Label;
import java.lang.classfile.instruction.InvokeInstruction;
import java.lang.constant.ClassDesc;
import java.lang.constant.MethodTypeDesc;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

/** Local compatibility transform for the unmodified Dynamic Seasons 7.1.4 release. */
public final class FixSeasonBlockOptions {
    private static final String INPUT_SHA256 = "78CB995BC63F7C2BE4FADA20C99B87245FAA1C5B84EF88681788A8C8BE806F33";
    private static final String CLASS = "DynamicSeasons/content/interaction/ChangeBlockOptionsInteraction";
    private static final String ENTRY = CLASS + ".class";

    public static void main(String[] arguments) throws Exception {
        if (arguments.length != 2) throw new IllegalArgumentException("Expected input and output JAR paths.");
        Path input = Path.of(arguments[0]);
        Path output = Path.of(arguments[1]);
        String originalHash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(input)));
        if (!originalHash.equalsIgnoreCase(INPUT_SHA256)) throw new IllegalArgumentException("Input must be the reviewed upstream 7.1.4 release.");
        if (Files.exists(output)) throw new IllegalArgumentException("Output already exists.");

        try (ZipFile original = new ZipFile(input.toFile());
             ZipOutputStream patched = new ZipOutputStream(Files.newOutputStream(output))) {
            var entries = original.entries();
            int changed = 0;
            while (entries.hasMoreElements()) {
                ZipEntry source = entries.nextElement();
                byte[] contents;
                try (InputStream stream = original.getInputStream(source)) { contents = stream.readAllBytes(); }
                if (source.getName().equals(ENTRY)) {
                    contents = fix(contents);
                    changed++;
                }
                ZipEntry destination = new ZipEntry(source.getName());
                destination.setTime(source.getTime());
                if (source.getComment() != null) destination.setComment(source.getComment());
                if (source.getExtra() != null) destination.setExtra(source.getExtra());
                patched.putNextEntry(destination);
                patched.write(contents);
                patched.closeEntry();
            }
            if (changed != 1) throw new IllegalStateException("Expected exactly one modified class.");
        }
    }

    private static byte[] fix(byte[] original) {
        ClassFile classFile = ClassFile.of();
        ClassModel model = classFile.parse(original);
        ClassDesc owner = ClassDesc.ofInternalName(CLASS);
        ClassDesc map = ClassDesc.of("it.unimi.dsi.fastutil.ints.Int2IntMap");
        int[] edits = new int[3];

        ClassTransform publishMap = (builder, element) -> {
            if (element instanceof FieldModel field && field.fieldName().equalsString("changeMapIds")) {
                builder.transformField(field, (fieldBuilder, fieldElement) -> {
                    if (fieldElement instanceof AccessFlags flags) {
                        fieldBuilder.withFlags(flags.flagsMask() | ClassFile.ACC_VOLATILE);
                        edits[0]++;
                    } else fieldBuilder.with(fieldElement);
                });
            } else builder.with(element);
        };

        ClassTransform deferDecode = ClassTransform.transformingMethodBodies(
            method -> method.methodName().equalsString("<clinit>"), (builder, element) -> {
                if (element instanceof InvokeInstruction call && call.name().equalsString("afterDecode") &&
                    call.owner().asInternalName().equals("com/hypixel/hytale/codec/builder/BuilderCodec$Builder")) {
                    // Discard the consumer. The following upstream POP still discards the builder.
                    builder.pop();
                    edits[1]++;
                } else builder.with(element);
            });

        ClassTransform initializeOnUse = ClassTransform.transformingMethodBodies(
            method -> method.methodName().equalsString("interactWithBlock"), new CodeTransform() {
                @Override public void atStart(CodeBuilder builder) {
                    Label ready = builder.newLabel();
                    builder.aload(0).getfield(owner, "changeMapIds", map).ifnonnull(ready)
                        .aload(0).invokevirtual(owner, "processConfig", MethodTypeDesc.of(ClassDesc.ofDescriptor("V")))
                        .labelBinding(ready);
                    edits[2]++;
                }
                @Override public void accept(CodeBuilder builder, CodeElement element) { builder.with(element); }
            });

        byte[] result = classFile.transformClass(model, publishMap.andThen(deferDecode).andThen(initializeOnUse));
        if (edits[0] != 1 || edits[1] != 1 || edits[2] != 1)
            throw new IllegalStateException("Upstream class shape changed. Do not apply this transform.");
        if (!classFile.verify(result).isEmpty()) throw new IllegalStateException("Patched class failed bytecode verification.");
        return result;
    }
}
