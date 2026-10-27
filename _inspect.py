import inspect, meta_sam_parser as p
print(inspect.getsource(p.decode_mask_to_raster)[:1500])
from meta_sam_parser import SegmentationMask, SegmentationMaskEncoding
print("---- SegmentationMask annotations:", getattr(SegmentationMask, "__annotations__", None))
print("---- encodings:", list(SegmentationMaskEncoding))
