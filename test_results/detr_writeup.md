# DETR: DEtection TRansformer

## Overview

DETR (DEtection TRansformer) is an object detection architecture introduced by Facebook Research
in 2020 in the paper *"End-to-End Object Detection with Transformers"* (Carion et al.). It was
the first work to successfully apply the Transformer architecture — originally designed for NLP —
directly to object detection, eliminating the need for hand-crafted components like anchor boxes
and non-maximum suppression (NMS) that had dominated the field for years.

---

## The Problem with Prior Approaches

Before DETR, state-of-the-art object detectors (Faster R-CNN, YOLO, SSD) all shared a common
structure:

1. Generate candidate regions or anchor boxes across the image
2. Score and classify each candidate
3. Run NMS to remove duplicate detections

This pipeline works well but has significant drawbacks:
- **Anchors are hand-designed** — their scales and aspect ratios are tuned per-dataset
- **NMS is a post-processing heuristic** — not learned, not differentiable
- **Two-stage complexity** — region proposal followed by classification adds engineering overhead
- **Difficult to reason about globally** — predictions are made locally per anchor without full
  scene context

---

## DETR's Approach

DETR reframes detection as a **direct set prediction problem**: given an image, predict the set
of all objects in it in one shot. There is no anchor generation, no NMS, and no region proposals.

### Architecture

```
Image
  └─► CNN Backbone (ResNet-50)
        └─► Flattened feature map + positional encodings
              └─► Transformer Encoder (self-attention over all spatial positions)
                    └─► Transformer Decoder (N learned object queries → N predictions)
                          └─► FFN heads → (class, bounding box) × N
```

**CNN Backbone** extracts a spatial feature map from the input image (e.g., ResNet-50 outputs a
feature map of shape C×H/32×W/32).

**Transformer Encoder** runs self-attention across all spatial positions of the flattened feature
map. Each position can attend to every other position, giving the model global scene context from
the start. Positional encodings are added to preserve spatial structure.

**Transformer Decoder** takes N learned vectors called *object queries* as input. These are
trainable embeddings — not anchors, not proposals — that the decoder learns to use to "ask"
different questions about the image (e.g., "is there an object in the top-left?"). Cross-attention
between the queries and the encoder output lets each query gather evidence from the full image.
The decoder outputs N prediction slots in parallel.

**Feed-forward heads** map each of the N decoder outputs to a (class label, bounding box)
prediction. If fewer than N objects are present, the remaining slots predict a special "no object"
(∅) class.

### Bipartite Matching Loss

The key training innovation is how predictions are matched to ground-truth boxes. Since both are
unordered sets, DETR uses the **Hungarian algorithm** to find the optimal one-to-one assignment
between the N predictions and the M ground-truth objects (with N > M, so M predictions are matched
to objects and the rest to ∅). The loss is then computed only on matched pairs.

This eliminates duplicates without NMS — the model is trained directly to produce exactly one
prediction per object.

---

## Strengths

- **Truly end-to-end** — one loss, one forward pass, no post-processing pipeline
- **Global reasoning** — self-attention sees the entire image simultaneously, making it naturally
  good at detecting objects in context (e.g., crowded scenes, occluded objects)
- **Simple architecture** — removes entire subsystems (RPN, anchor matching, NMS)
- **Extensible** — the same approach was later adapted for segmentation (DETR with masks),
  panoptic segmentation, and tracking

## Weaknesses

- **Slow training convergence** — DETR requires ~500 epochs to match Faster R-CNN trained for
  ~37 epochs. The attention mechanism needs many iterations to learn to focus on individual objects
- **Poor performance on small objects** — the coarse feature map (stride 32) loses fine-grained
  spatial detail, hurting detection of small objects
- **Quadratic attention cost** — self-attention over the spatial feature map scales as O((HW)²),
  which is expensive for high-resolution images

---

## Key Follow-up Work

The weaknesses above motivated a wave of follow-up models:

**Deformable DETR** (2021) — replaces full attention with *deformable attention* that attends to
a small set of sampled points around each query location. Trains in 10× fewer epochs and handles
multi-scale features, fixing the small-object problem.

**DAB-DETR** (2022) — uses dynamic anchor boxes as object queries, making queries spatially
interpretable and improving convergence.

**DINO** (2022) — combines deformable attention with improved query initialization and contrastive
denoising training. Became the de facto strong DETR-family baseline.

**RT-DETR** (2023, Baidu) — real-time variant using a hybrid encoder and cached attention,
achieving competitive speed with YOLO-class models.

---

## The Model Used in This App

The app uses `TahaDouaji/detr-doc-table-detection`, a DETR-base model (ResNet-50 backbone)
fine-tuned on document images to detect two classes: **table** and **table rotated**.

It was chosen for this task because:
- Tables are large, well-defined rectangular regions — exactly the kind of object full-attention
  DETR handles well (the small-object weakness doesn't apply)
- The training domain (document scans) matches the app's input
- HuggingFace's `transformers` pipeline API makes inference simple

In the app's pipeline, DETR runs on each full page image and returns bounding boxes for any tables
found. Those regions are cropped and passed to PaddleOCR. Without this step, OCR would run on the
entire page and mix table data with surrounding text.

---

## References

- Carion et al., *End-to-End Object Detection with Transformers*, ECCV 2020.
  https://arxiv.org/abs/2005.12872
- Zhu et al., *Deformable DETR*, ICLR 2021. https://arxiv.org/abs/2010.04159
- Zhang et al., *DINO: DETR with Improved DeNoising Anchor Boxes*, ICLR 2023.
  https://arxiv.org/abs/2203.03605
- HuggingFace model card: https://huggingface.co/TahaDouaji/detr-doc-table-detection
