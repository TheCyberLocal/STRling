package com.strling.jvm;

import com.sun.jna.IntegerType;
import com.sun.jna.Library;
import com.sun.jna.Native;
import com.sun.jna.Pointer;
import com.sun.jna.Structure;

interface InteropLibrary extends Library {
    int strling_interop_abi_version_v1();

    int strling_interop_execute_v1(Pointer input, SizeT inputLength, OwnedBytes output);

    int strling_interop_owned_bytes_free_v1(OwnedBytes output);

    final class SizeT extends IntegerType {
        public SizeT() {
            this(0L);
        }

        public SizeT(long value) {
            super(Native.SIZE_T_SIZE, value, true);
        }
    }

    @Structure.FieldOrder({"data", "len"})
    final class OwnedBytes extends Structure {
        public Pointer data;
        public SizeT len;

        public OwnedBytes() {
            len = new SizeT();
        }
    }
}
