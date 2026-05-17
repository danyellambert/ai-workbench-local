# PDF Extraction Benchmark Review

Generated at: 2026-03-15 01:12:42
Provider: ollama · Model: qwen2.5:7b · Prompt profile: neutral

## How to use this review file

For each question, fill in:
- `manual_score`: 0, 1, or 2
- `manual_notes`: comments about answer quality, retrieval quality, and noise

---

Review packet: 07
Document: Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf
Mode: basic — Básico · pypdf apenas · mais rápido
Questions in this packet: 16

### Mode: basic — Básico · pypdf apenas · mais rápido

- Extraction time: 0.185 s
- Indexing time: 3.689 s
- Final characters: 36778
- Chunks: 37
- Docling mode: none
- Suspicious pages: [1, 3, 5, 6, 8]
- Pages processed with Docling: []

#### Question 1

**Question:** What main problem does the paper try to solve?

**Retrieval backend:** chroma
**Retrieval time:** 0.146 s
**Generation time:** 9.247 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.4551, "vector_score": 0.4983, "lexical_score": 0.375, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 19, "score": 0.4354, "vector_score": 0.4679, "lexical_score": 0.375, "snippet": "(4), ∆k is the ﬁxed\ninterval in Eq.(7) for sampling k and\nh =\nθj\nks\n− θi\nks−1\n∆k\n. (12)\nAfter G is constructed, the optimization of Eq.(4) turns\nout to be ﬁnding an optimal path that passes through G and\nmaximizes the total sum of the weights of edges on the path.\nBy adding a virtual starting node and ending node to the\nleft and right side of G respectively, the problem turns to\nbe a classic longe"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 7, "score": 0.4211, "vector_score": 0.5132, "lexical_score": 0.25, "snippet": "as an\nenergy minimization problem on the states of CCs. A cost\nfunction that encodes the interactions between text lines\nand the curvilinearity of each text line is proposed. Their\nmethod is robust to the interference between text lines, spa-\ntially varying skew and irregular inter-character distance.\nIn comparison to the tracing based approaches, the methods\nusing CCs clustering are generally mor"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 32, "score": 0.417, "vector_score": 0.5069, "lexical_score": 0.25, "snippet": "nes by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Página 9]\nReferences\n[1] S. Avidan and A. Shamir. Seam carving for content-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dins"}]`

**Generated answer:**

The paper tries to solve the problem of extracting virtual baselines from document images, especially those with curved or non-linear baselines. The main challenge addressed is accurately identifying the baseline lines that guide the alignment of printed content on a document page, even when these lines are not perfectly straight or intersect each other.

- manual_score: 2
- manual_notes: Correct main problem and grounded in the abstract snippet; only minor extra wording. 

#### Question 2

**Question:** What core observations motivate the proposed method?

**Retrieval backend:** chroma
**Retrieval time:** 0.197 s
**Generation time:** 7.627 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.542, "vector_score": 0.5261, "lexical_score": 0.5714, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 21, "score": 0.4921, "vector_score": 0.5263, "lexical_score": 0.4286, "snippet": "d baseline is further smoothed by a cubic spline.\n3. Experimental Results\nTo test the performance of the proposed method, we car-\nried out a series of experiments on a great number of curved\ndocument images. These testing images include samples of\nscanned book pages and pages captured from books, maga-\nzines and paper sheets by a hand-held camera. In the exper-\niments, we empirically set the expon"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 6, "score": 0.4907, "vector_score": 0.5241, "lexical_score": 0.4286, "snippet": "a set of points along a text line are\nsimilar to each other. They thereby propose an interesting\nline tracing method based on self-similarity measure be-\ntween image patches. A very similar idea is also used in\nLiang et al.’s work [12], where texture ﬂow is introduced for\ntracing curved text lines. However, the tracing based meth-\nods are vulnerable to page layouts, changes of font sizes and\nnon-t"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 7, "score": 0.4871, "vector_score": 0.5186, "lexical_score": 0.4286, "snippet": "as an\nenergy minimization problem on the states of CCs. A cost\nfunction that encodes the interactions between text lines\nand the curvilinearity of each text line is proposed. Their\nmethod is robust to the interference between text lines, spa-\ntially varying skew and irregular inter-character distance.\nIn comparison to the tracing based approaches, the methods\nusing CCs clustering are generally mor"}]`

**Generated answer:**

The core observations that motivate the proposed method are:

1. The baselines of documents do not intersect with each other.
2. Within a narrow strip, the baselines can be well approximated by linear segments.

These observations led the researchers to propose a curvilinear projection-based method, which models the estimation of curved baselines as a constrained sequential optimization problem.

- manual_score: 2
- manual_notes: Correct and directly supported by the snippet listing the two motivating observations. 

#### Question 3

**Question:** What does Figure 1 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.262 s
**Generation time:** 13.956 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 31, "score": 0.397, "vector_score": 0.4762, "lexical_score": 0.25, "snippet": "s σ ranging from 0 to 12 by a ﬁxed step 2. (top) the extracted\nbaselines overlapping on the blurring images, (bottom) the close-up patches for details illustration.\nFigure 9. Comparisons of our method with Koo and Cho’s method [9]. (a) the curved document images, (b) edge maps used by Koo and\nCho’s method, (c) text-lines extraction and ﬁtting by Koo and Cho’s method, (d) edge maps used by our meth"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 21, "score": 0.3879, "vector_score": 0.4621, "lexical_score": 0.25, "snippet": "d baseline is further smoothed by a cubic spline.\n3. Experimental Results\nTo test the performance of the proposed method, we car-\nried out a series of experiments on a great number of curved\ndocument images. These testing images include samples of\nscanned book pages and pages captured from books, maga-\nzines and paper sheets by a hand-held camera. In the exper-\niments, we empirically set the expon"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 20, "score": 0.3859, "vector_score": 0.459, "lexical_score": 0.25, "snippet": "e estimated\nbaselines are much better in separability.\nFigure 5. Results of the estimated baselines on the strip in Fig-\nure 3(a). (a) the solved optimal path (red curve) on R, (b) the\nestimated baselines on the strip, (c) the projection proﬁles of strip\nalong a ﬁxed direction, (d) the projection proﬁles of strip along the\nestimated baselines.\n2.3. Baselines Connection Between Strips\nAfter the bas"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 17, "score": 0.3808, "vector_score": 0.4513, "lexical_score": 0.25, "snippet": "directed graph G. (a) only\ntwo vertices having adjacent k-coordinates can be connected by a\ndirected edge, (b) deriving the non-intersection condition of two\nadjacent projection lines.\nSimilarly, taking samples of k between [1, H] by a ﬁxed\ninterval ∆k gives\n1 = k1 < k 2 < · · · < k n− 1 < k n = H. (7)\nWe then construct a weighted directed graph G with to-\ntally m × n vertices on the discretized k"}]`

**Generated answer:**

Based on the context provided, Figure 10 is described, not Figure 1. Figure 10 compares the method described in the paper with other methods. Specifically, it shows:

- Curved document images (a)
- Coarse baseline estimations by Tian and Narasimhan’s method (b)
- Refinement results of Tian and Narasimhan’s method (c)
- Separating seams produced by Nikolaos and Sabine’s method (d)
- Estimated baselines by Nikolaos and Sabine’s method (e)
- Extracted baselines by the method described in the paper (f)

There is no specific description of Figure 1 in the given context. If you need information about Figure 1, it might be helpful to provide more details or check the full paper.

- manual_score: 1
- manual_notes: Reasonable that the snippets do not show Figure 1, but the answer adds unsupported details about other figures. 

#### Question 4

**Question:** What does Figure 2 illustrate?

**Retrieval backend:** chroma
**Retrieval time:** 0.277 s
**Generation time:** 4.519 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 31, "score": 0.3749, "vector_score": 0.4421, "lexical_score": 0.25, "snippet": "s σ ranging from 0 to 12 by a ﬁxed step 2. (top) the extracted\nbaselines overlapping on the blurring images, (bottom) the close-up patches for details illustration.\nFigure 9. Comparisons of our method with Koo and Cho’s method [9]. (a) the curved document images, (b) edge maps used by Koo and\nCho’s method, (c) text-lines extraction and ﬁtting by Koo and Cho’s method, (d) edge maps used by our meth"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 21, "score": 0.3648, "vector_score": 0.4266, "lexical_score": 0.25, "snippet": "d baseline is further smoothed by a cubic spline.\n3. Experimental Results\nTo test the performance of the proposed method, we car-\nried out a series of experiments on a great number of curved\ndocument images. These testing images include samples of\nscanned book pages and pages captured from books, maga-\nzines and paper sheets by a hand-held camera. In the exper-\niments, we empirically set the expon"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 20, "score": 0.3552, "vector_score": 0.4118, "lexical_score": 0.25, "snippet": "e estimated\nbaselines are much better in separability.\nFigure 5. Results of the estimated baselines on the strip in Fig-\nure 3(a). (a) the solved optimal path (red curve) on R, (b) the\nestimated baselines on the strip, (c) the projection proﬁles of strip\nalong a ﬁxed direction, (d) the projection proﬁles of strip along the\nestimated baselines.\n2.3. Baselines Connection Between Strips\nAfter the bas"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 18, "score": 0.353, "vector_score": 0.4084, "lexical_score": 0.25, "snippet": "ects with the two vertical boundaries of a strip at A and B\nrespectively, as illustrated in Figure 4(b). The v-coordinates\nof A and B in the image coordinate system of strip can be\ncomputed respectively as:\nvA = ks− 1 − w\n2 cot θi\nks−1 , (8)\nvB = ks− 1 + w\n2 cot θi\nks−1 , (9)\nwhere w is the width of the strip.\nAs illustrated in Figure 4(b), to avoid the intersection of\nthe projection line with its"}]`

**Generated answer:**

The context provided does not contain any information about Figure 2. The descriptions and figures mentioned are Figure 6, Figure 9, and Figure 10. Therefore, I cannot provide what Figure 2 illustrates based on the given context.

- manual_score: 1
- manual_notes: Mostly fair that Figure 2 is not supported by the shown snippets, but it mentions other figures not evidenced here. 

#### Question 5

**Question:** What does Figure 3 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.197 s
**Generation time:** 12.117 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 20, "score": 0.3893, "vector_score": 0.4643, "lexical_score": 0.25, "snippet": "e estimated\nbaselines are much better in separability.\nFigure 5. Results of the estimated baselines on the strip in Fig-\nure 3(a). (a) the solved optimal path (red curve) on R, (b) the\nestimated baselines on the strip, (c) the projection proﬁles of strip\nalong a ﬁxed direction, (d) the projection proﬁles of strip along the\nestimated baselines.\n2.3. Baselines Connection Between Strips\nAfter the bas"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 21, "score": 0.3812, "vector_score": 0.4518, "lexical_score": 0.25, "snippet": "d baseline is further smoothed by a cubic spline.\n3. Experimental Results\nTo test the performance of the proposed method, we car-\nried out a series of experiments on a great number of curved\ndocument images. These testing images include samples of\nscanned book pages and pages captured from books, maga-\nzines and paper sheets by a hand-held camera. In the exper-\niments, we empirically set the expon"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 31, "score": 0.3732, "vector_score": 0.4396, "lexical_score": 0.25, "snippet": "s σ ranging from 0 to 12 by a ﬁxed step 2. (top) the extracted\nbaselines overlapping on the blurring images, (bottom) the close-up patches for details illustration.\nFigure 9. Comparisons of our method with Koo and Cho’s method [9]. (a) the curved document images, (b) edge maps used by Koo and\nCho’s method, (c) text-lines extraction and ﬁtting by Koo and Cho’s method, (d) edge maps used by our meth"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 19, "score": 0.3626, "vector_score": 0.4232, "lexical_score": 0.25, "snippet": "(4), ∆k is the ﬁxed\ninterval in Eq.(7) for sampling k and\nh =\nθj\nks\n− θi\nks−1\n∆k\n. (12)\nAfter G is constructed, the optimization of Eq.(4) turns\nout to be ﬁnding an optimal path that passes through G and\nmaximizes the total sum of the weights of edges on the path.\nBy adding a virtual starting node and ending node to the\nleft and right side of G respectively, the problem turns to\nbe a classic longe"}]`

**Generated answer:**

The context provided does not contain a direct description of what Figure 3 shows. However, based on the information given, Figure 3 appears to be related to the strips and baselines discussed in the document. Specifically, Figure 5 is mentioned to show results of estimated baselines on a strip, which is related to the process described for strips and baselines. Since Figure 3 is not directly referenced in the provided context, we cannot determine its exact content without additional information. If Figure 3 is related to strips and baselines as in Figure 5, it likely shows strips and the process of estimating baselines on those strips.

- manual_score: 1
- manual_notes: Notes the lack of direct evidence, but then speculates about Figure 3, so grounding is weak. 

#### Question 6

**Question:** What does Figure 5 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.183 s
**Generation time:** 11.326 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 19, "score": 0.3832, "vector_score": 0.455, "lexical_score": 0.25, "snippet": "(4), ∆k is the ﬁxed\ninterval in Eq.(7) for sampling k and\nh =\nθj\nks\n− θi\nks−1\n∆k\n. (12)\nAfter G is constructed, the optimization of Eq.(4) turns\nout to be ﬁnding an optimal path that passes through G and\nmaximizes the total sum of the weights of edges on the path.\nBy adding a virtual starting node and ending node to the\nleft and right side of G respectively, the problem turns to\nbe a classic longe"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 20, "score": 0.3805, "vector_score": 0.4507, "lexical_score": 0.25, "snippet": "e estimated\nbaselines are much better in separability.\nFigure 5. Results of the estimated baselines on the strip in Fig-\nure 3(a). (a) the solved optimal path (red curve) on R, (b) the\nestimated baselines on the strip, (c) the projection proﬁles of strip\nalong a ﬁxed direction, (d) the projection proﬁles of strip along the\nestimated baselines.\n2.3. Baselines Connection Between Strips\nAfter the bas"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 31, "score": 0.3789, "vector_score": 0.4483, "lexical_score": 0.25, "snippet": "s σ ranging from 0 to 12 by a ﬁxed step 2. (top) the extracted\nbaselines overlapping on the blurring images, (bottom) the close-up patches for details illustration.\nFigure 9. Comparisons of our method with Koo and Cho’s method [9]. (a) the curved document images, (b) edge maps used by Koo and\nCho’s method, (c) text-lines extraction and ﬁtting by Koo and Cho’s method, (d) edge maps used by our meth"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 21, "score": 0.363, "vector_score": 0.4238, "lexical_score": 0.25, "snippet": "d baseline is further smoothed by a cubic spline.\n3. Experimental Results\nTo test the performance of the proposed method, we car-\nried out a series of experiments on a great number of curved\ndocument images. These testing images include samples of\nscanned book pages and pages captured from books, maga-\nzines and paper sheets by a hand-held camera. In the exper-\niments, we empirically set the expon"}]`

**Generated answer:**

Figure 5 shows the results of the estimated baselines on a strip. Specifically:

- (a) illustrates the solved optimal path (in red) on R.
- (b) shows the estimated baselines on the strip.
- (c) displays the projection profiles of the strip along a fixed direction.
- (d) shows the projection profiles of the strip along the estimated baselines.

The figure compares the projections along a fixed direction with those along the estimated baselines, highlighting that the projections along the estimated baselines are better in separability.

- manual_score: 2
- manual_notes: Correct and well supported by the Figure 5 caption snippet, including the four subparts. 

#### Question 7

**Question:** At a high level, how does the curvilinear projection work?

**Retrieval backend:** chroma
**Retrieval time:** 0.291 s
**Generation time:** 12.216 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 29, "score": 0.5867, "vector_score": 0.6334, "lexical_score": 0.5, "snippet": "trip, it requires the available visual cues within the\nstrip to be dominant. As a result, the projection may fail if\nan image strip consists of very sparse visual cues or large\nareas of non-textual objects that have too little available in-\nformation to infer the correct projection direction. This case\ngenerally occurs to page margins, where insufﬁcient cues\nare available for the correct estimatio"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 9, "score": 0.5294, "vector_score": 0.6125, "lexical_score": 0.375, "snippet": "large areas of non-textual objects in images.\nIn this paper, we propose a novel curvilinear projec-\ntion based method for accurate extraction of curved base-\nlines from a distorted document image. Our method comes\nfrom two basic observations that the baselines of a curved\ndocument image do not intersect with each other and that\nwithin a narrow vertical strip, the baselines can be well ap-\nproximat"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 8, "score": 0.5281, "vector_score": 0.6105, "lexical_score": 0.375, "snippet": "ter improve the method by in-\ncorporating some constraints into the optimization proce-\ndure to yield more robust separating seams. The segmen-\ntation based methods are more general-purpose and require\nless knowledge about document layouts and scripts. How-\never, these methods share the similar limitations that most\nsegmentation methods may have. They are sensitive to im-\nage noises, changes of im"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.5155, "vector_score": 0.5911, "lexical_score": 0.375, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}]`

**Generated answer:**

The curvilinear projection method works by leveraging two key observations:
1. The baselines of a curved document image do not intersect with each other.
2. Within a narrow vertical strip, the baselines can be well approximated by linear segments.

Based on these observations, the method models the baseline extraction as a constrained sequential optimization problem on the projection map of vertical strips. A dynamic programming algorithm is then used to efficiently solve this problem, allowing for the accurate extraction of curved baselines from the image.

This approach is segment-free, meaning it directly extracts the curved baselines without relying on intermediate segmentation steps. It is also highly efficient and robust to various image conditions, including non-textual objects, changes in image resolution, and image quality degradation.

- manual_score: 1
- manual_notes: Core description is supported, but the answer adds unsupported claims about being segment-free, highly efficient, and broadly robust. 

#### Question 8

**Question:** Which algorithm is used to solve the optimization problem?

**Retrieval backend:** chroma
**Retrieval time:** 0.26 s
**Generation time:** 8.38 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 19, "score": 0.7198, "vector_score": 0.5689, "lexical_score": 1.0, "snippet": "(4), ∆k is the ﬁxed\ninterval in Eq.(7) for sampling k and\nh =\nθj\nks\n− θi\nks−1\n∆k\n. (12)\nAfter G is constructed, the optimization of Eq.(4) turns\nout to be ﬁnding an optimal path that passes through G and\nmaximizes the total sum of the weights of edges on the path.\nBy adding a virtual starting node and ending node to the\nleft and right side of G respectively, the problem turns to\nbe a classic longe"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.6193, "vector_score": 0.4912, "lexical_score": 0.8571, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 16, "score": 0.5545, "vector_score": 0.4684, "lexical_score": 0.7143, "snippet": "side to the right side under the non-intersection constraints.\nThis problem can be efﬁciently solved by a dynamic pro-\ngramming method.\nThere are many ways to deﬁne the smoothness mea-\nsure. Here we give an example of the ﬁrst-order smoothness\nterms, which is deﬁned on two adjacent angles, i.e.,\nφ(θ1, · · · , θH ) =\nH∑\nk=2\nexp\n(\n− (θk − θk− 1)2\n2σ2\n)\n, (5)\nwhere σ is used to control the sensitivit"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 15, "score": 0.5359, "vector_score": 0.5168, "lexical_score": 0.5714, "snippet": "explicitly give the projection value of the strip along any\nline passing through a point on L. Figure 3 illustrates the\nobtained projection map from Radon transform.\n2.2.2 Optimized strip projection\nWe can estimate the optimal projection lines across the cen-\ntral line L of a strip by solving the following constrained\noptimization problem, i.e.,\nmax\nθ1,···,θH\nH∑\nk=1\nRp(k, θk) + λφ(θ1, · · · , θH )"}]`

**Generated answer:**

The optimization problem is efficiently solved by Dijkstra's algorithm after adding a virtual starting node and ending node to the left and right side of the graph G, respectively. This transforms the problem into a classic longest path problem.

- manual_score: 0
- manual_notes: Unsupported/wrong: the shown snippets say the problem is solved by dynamic programming, not specifically Dijkstra's algorithm. 

#### Question 9

**Question:** What are the main experimental results described in the paper?

**Retrieval backend:** chroma
**Retrieval time:** 0.292 s
**Generation time:** 17.853 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 21, "score": 0.5045, "vector_score": 0.5069, "lexical_score": 0.5, "snippet": "d baseline is further smoothed by a cubic spline.\n3. Experimental Results\nTo test the performance of the proposed method, we car-\nried out a series of experiments on a great number of curved\ndocument images. These testing images include samples of\nscanned book pages and pages captured from books, maga-\nzines and paper sheets by a hand-held camera. In the exper-\niments, we empirically set the expon"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 20, "score": 0.4911, "vector_score": 0.4863, "lexical_score": 0.5, "snippet": "e estimated\nbaselines are much better in separability.\nFigure 5. Results of the estimated baselines on the strip in Fig-\nure 3(a). (a) the solved optimal path (red curve) on R, (b) the\nestimated baselines on the strip, (c) the projection proﬁles of strip\nalong a ﬁxed direction, (d) the projection proﬁles of strip along the\nestimated baselines.\n2.3. Baselines Connection Between Strips\nAfter the bas"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 22, "score": 0.4864, "vector_score": 0.479, "lexical_score": 0.5, "snippet": "strates some example results of baseline ex-\ntraction by our method on curved binary document images\nfrom the DFKI dataset 1. This publicly available dataset is\nspecially designed for the evaluation of various methods on\ngeometric distortion rectiﬁcation of curved document im-\nages. From the results, we can see that the proposed method\ncan extract the curved baselines in a high accuracy. The\nestim"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 31, "score": 0.4595, "vector_score": 0.505, "lexical_score": 0.375, "snippet": "s σ ranging from 0 to 12 by a ﬁxed step 2. (top) the extracted\nbaselines overlapping on the blurring images, (bottom) the close-up patches for details illustration.\nFigure 9. Comparisons of our method with Koo and Cho’s method [9]. (a) the curved document images, (b) edge maps used by Koo and\nCho’s method, (c) text-lines extraction and ﬁtting by Koo and Cho’s method, (d) edge maps used by our meth"}]`

**Generated answer:**

The main experimental results described in the paper include:

1. The proposed method was tested on a large number of curved document images, including scanned book pages and pages captured from books, magazines, and paper sheets by a handheld camera.

2. The method successfully extracted curved baselines with high accuracy, even in the presence of marginal noises and non-textual objects like inserted formulas and photos.

3. The extracted baselines were robust to non-textual objects and could infer baselines in blank areas and non-textual regions by exploiting visual cues such as text lines, horizontal lines in tables, and page boundaries.

4. The method performed well on both binary and grayscale document images.

5. Comparisons with other methods (Koo and Cho’s method [9], Tian and Narasimhan’s method [25], and Nikolaos and Sabine’s method [19]) showed that the proposed method outperformed these methods in terms of baseline extraction accuracy and robustness to non-textual objects.

6. The method was validated using the DFKI dataset, which is specifically designed for evaluating methods on geometric distortion rectification of curved document images.

7. The results demonstrated that the proposed method could effectively handle images with large areas of non-textual objects.

- manual_score: 1
- manual_notes: Partially supported by the experiment and DFKI snippets, but many details and comparison claims go beyond the shown evidence. 

#### Question 10

**Question:** According to the paper, what kinds of robustness does the method demonstrate?

**Retrieval backend:** chroma
**Retrieval time:** 0.223 s
**Generation time:** 12.746 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 21, "score": 0.501, "vector_score": 0.5315, "lexical_score": 0.4444, "snippet": "d baseline is further smoothed by a cubic spline.\n3. Experimental Results\nTo test the performance of the proposed method, we car-\nried out a series of experiments on a great number of curved\ndocument images. These testing images include samples of\nscanned book pages and pages captured from books, maga-\nzines and paper sheets by a hand-held camera. In the exper-\niments, we empirically set the expon"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 25, "score": 0.4593, "vector_score": 0.5271, "lexical_score": 0.3333, "snippet": "nges\nof image resolutions. The robustness to image blurring will\nbeneﬁt the process of image noise removal, since we can\nchoose a larger kernel for image smoothing without signif-\n3930\n[Página 7]\nicantly losing the accuracy in baseline extraction. The ro-\nbustness to image blurring also means that the method is\ninsensitive to the touched neighboring characters and text\nlines. These cases are very "}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 24, "score": 0.4555, "vector_score": 0.5213, "lexical_score": 0.3333, "snippet": "tracted baselines overlapped, the edge maps and the close-up image patches, respectively. The left-most three images come\nfrom English documents and the right-most four images come from Chinese documents. The last image is a scanned book page.\nOut-of-focus blurring commonly happens to a camera-\ncaptured document image. This is because that the camera\nis hard to focus accurately on the document pag"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 22, "score": 0.4491, "vector_score": 0.5115, "lexical_score": 0.3333, "snippet": "strates some example results of baseline ex-\ntraction by our method on curved binary document images\nfrom the DFKI dataset 1. This publicly available dataset is\nspecially designed for the evaluation of various methods on\ngeometric distortion rectiﬁcation of curved document im-\nages. From the results, we can see that the proposed method\ncan extract the curved baselines in a high accuracy. The\nestim"}]`

**Generated answer:**

According to the paper, the method demonstrates robustness to:

1. Image blurring: The method yields stable results even for images with different levels of blurring, as shown in Figure 8 and discussed in the context.

2. Changes in image resolutions: The robustness to image blurring also implies that the method is not sensitive to changes in image resolutions.

3. Out-of-focus blurring: The method performs well on blurred images, as demonstrated in Figure 8.

4. Marginal noises and non-textual objects: The method can correctly extract curved baselines even in the presence of such elements, as shown in Figures 6 and 10.

5. Various document types: The method works well on both binary and gray-scale document images, including those from books, magazines, and paper sheets, as shown in Figures 6, 7, and 10.

- manual_score: 1
- manual_notes: Blurring and resolution robustness are supported, but the rest of the listed robustness claims are only weakly grounded or unsupported here. 

#### Question 11

**Question:** What is the central topic of the document?

**Retrieval backend:** chroma
**Retrieval time:** 0.317 s
**Generation time:** 9.043 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 32, "score": 0.4537, "vector_score": 0.4826, "lexical_score": 0.4, "snippet": "nes by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Página 9]\nReferences\n[1] S. Avidan and A. Shamir. Seam carving for content-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dins"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.4489, "vector_score": 0.4752, "lexical_score": 0.4, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 1, "score": 0.4475, "vector_score": 0.4731, "lexical_score": 0.4, "snippet": "[Página 1]\nExtraction of Virtual Baselines from Distorted Document Images\nUsing Curvilinear Projection\nGaofeng MENG∗†, Zuming HUANG†, Y onghong SONG‡,\nShiming XIANG† and Chunhong PAN†\n† National Laboratory of Pattern Recognition, Institute of Automation\nChinese Academy of Sciences, Beijing P .R.China, 100190\nEmail: {gfmeng, smxiang, chpan }@nlpr.ia.ac.cn, huangzuming2014@ia.ac.cn\n‡ Institute of Ar"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 36, "score": 0.4396, "vector_score": 0.461, "lexical_score": 0.4, "snippet": "and S. Datta. Segmentation of bangla unconstrained\nhandwritten text. In Proceedings of the 7th International\nConference on Document Analysis and Recognition , pages\n1128–1132, Aug 2003.\n[21] V . Papavassiliou, T. Stafylakis, V . Katsouros, and\nG. Carayannis. Handwritten document image segmen-\ntation into text lines and words. Pattern Recognition ,\n43(1):369 – 377, 2010.\n[22] M. Pilu. Extraction of"}]`

**Generated answer:**

The central topic of the document is the accurate extraction of virtual baselines from distorted document images, particularly curved ones. The authors propose an efficient method based on two key observations about document baselines and develop a curvilinear projection method to achieve this.

- manual_score: 2
- manual_notes: Correct and supported by the title and abstract snippets. 

#### Question 12

**Question:** What are the 3 most important sections or takeaways?

**Retrieval backend:** chroma
**Retrieval time:** 0.207 s
**Generation time:** 16.353 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 8, "score": 0.4112, "vector_score": 0.4018, "lexical_score": 0.4286, "snippet": "ter improve the method by in-\ncorporating some constraints into the optimization proce-\ndure to yield more robust separating seams. The segmen-\ntation based methods are more general-purpose and require\nless knowledge about document layouts and scripts. How-\never, these methods share the similar limitations that most\nsegmentation methods may have. They are sensitive to im-\nage noises, changes of im"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 6, "score": 0.4089, "vector_score": 0.3983, "lexical_score": 0.4286, "snippet": "a set of points along a text line are\nsimilar to each other. They thereby propose an interesting\nline tracing method based on self-similarity measure be-\ntween image patches. A very similar idea is also used in\nLiang et al.’s work [12], where texture ﬂow is introduced for\ntracing curved text lines. However, the tracing based meth-\nods are vulnerable to page layouts, changes of font sizes and\nnon-t"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 5, "score": 0.3922, "vector_score": 0.4495, "lexical_score": 0.2857, "snippet": "To this end,\nhorizontal text lines in document images have to be ﬁrstly\nextracted. According to how the text lines are obtained,\nthese methods can be roughly classiﬁed into four major cat-\negories, i.e., the tracing based methods [3, 4, 24, 25], the\nclustering based methods [9, 10, 22, 27], the segmentation\nbased methods [11, 19, 23] and the projection based meth-\nods [20, 26, 2, 21].\nEarly method"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 4, "score": 0.3642, "vector_score": 0.4065, "lexical_score": 0.2857, "snippet": "been ex-\ntensively studied in the context of document image deskew-\ning [17] and image perspective rectiﬁcation [14, 22]. The\nproblem, however, gets worse when a document image is\ndistorted due to nonlinear page curl. This commonly hap-\npens when one captures the images of an opened thick and\n3925\n[Página 2]\nbound book by a hand-held camera.\nThe extraction of baselines is of great importance to\nma"}]`

**Generated answer:**

Based on the provided context, here are three important sections or takeaways:

1. **Text Line Extraction Methods**:
   - Text line extraction can be categorized into four main types: tracing-based, clustering-based, segmentation-based, and projection-based methods.
   - Each method has its strengths and limitations. For instance, projection-based methods are effective for handwritten text but struggle with distorted images and non-textual content.

2. **Challenges in Baseline Extraction**:
   - Extracting baselines is crucial for correcting geometric distortions in document images.
   - This process is challenging due to factors like image distortion, non-textual objects, and image quality issues such as blurring and low resolution.

3. **Proposed Novel Method**:
   - The paper proposes a novel curvilinear projection-based method for accurately extracting curved baselines from distorted document images.
   - This method aims to address the limitations of existing techniques by incorporating constraints into the optimization procedure to yield more robust separating seams.

These points summarize the key aspects of text line extraction methods, the challenges in baseline extraction, and the proposed solution in the paper.

- manual_score: 1
- manual_notes: Partial high-level summary from the related-work/problem snippets, but not clearly the document's three main sections and includes unsupported specifics. 

#### Question 13

**Question:** Does the document contain tables? What do they show?

**Retrieval backend:** chroma
**Retrieval time:** 0.285 s
**Generation time:** 9.969 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 22, "score": 0.5172, "vector_score": 0.5265, "lexical_score": 0.5, "snippet": "strates some example results of baseline ex-\ntraction by our method on curved binary document images\nfrom the DFKI dataset 1. This publicly available dataset is\nspecially designed for the evaluation of various methods on\ngeometric distortion rectiﬁcation of curved document im-\nages. From the results, we can see that the proposed method\ncan extract the curved baselines in a high accuracy. The\nestim"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 1, "score": 0.4817, "vector_score": 0.5391, "lexical_score": 0.375, "snippet": "[Página 1]\nExtraction of Virtual Baselines from Distorted Document Images\nUsing Curvilinear Projection\nGaofeng MENG∗†, Zuming HUANG†, Y onghong SONG‡,\nShiming XIANG† and Chunhong PAN†\n† National Laboratory of Pattern Recognition, Institute of Automation\nChinese Academy of Sciences, Beijing P .R.China, 100190\nEmail: {gfmeng, smxiang, chpan }@nlpr.ia.ac.cn, huangzuming2014@ia.ac.cn\n‡ Institute of Ar"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.4696, "vector_score": 0.5206, "lexical_score": 0.375, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 32, "score": 0.4336, "vector_score": 0.5324, "lexical_score": 0.25, "snippet": "nes by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Página 9]\nReferences\n[1] S. Avidan and A. Shamir. Seam carving for content-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dins"}]`

**Generated answer:**

Based on the information provided in the context, there is no explicit mention of tables within the document. However, the context does mention that the proposed method can robustly extract baselines even in the presence of non-textual objects, including "horizontal lines in tables". This suggests that while tables are not the primary focus, the method can handle and utilize horizontal lines from tables as visual cues for baseline extraction.

- manual_score: 1
- manual_notes: Fair that tables are not explicit in the shown snippets, but the answer adds unsupported discussion about table lines. 

#### Question 14

**Question:** Does the document contain figures or diagrams? What do they show?

**Retrieval backend:** chroma
**Retrieval time:** 0.279 s
**Generation time:** 9.206 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 32, "score": 0.4326, "vector_score": 0.5459, "lexical_score": 0.2222, "snippet": "nes by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Página 9]\nReferences\n[1] S. Avidan and A. Shamir. Seam carving for content-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dins"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 21, "score": 0.4274, "vector_score": 0.5379, "lexical_score": 0.2222, "snippet": "d baseline is further smoothed by a cubic spline.\n3. Experimental Results\nTo test the performance of the proposed method, we car-\nried out a series of experiments on a great number of curved\ndocument images. These testing images include samples of\nscanned book pages and pages captured from books, maga-\nzines and paper sheets by a hand-held camera. In the exper-\niments, we empirically set the expon"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.4231, "vector_score": 0.5313, "lexical_score": 0.2222, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 1, "score": 0.4212, "vector_score": 0.5284, "lexical_score": 0.2222, "snippet": "[Página 1]\nExtraction of Virtual Baselines from Distorted Document Images\nUsing Curvilinear Projection\nGaofeng MENG∗†, Zuming HUANG†, Y onghong SONG‡,\nShiming XIANG† and Chunhong PAN†\n† National Laboratory of Pattern Recognition, Institute of Automation\nChinese Academy of Sciences, Beijing P .R.China, 100190\nEmail: {gfmeng, smxiang, chpan }@nlpr.ia.ac.cn, huangzuming2014@ia.ac.cn\n‡ Institute of Ar"}]`

**Generated answer:**

Yes, the document contains figures. Specifically, Figure 6 is mentioned in the context provided. This figure illustrates some example results of baseline extraction by the proposed method on curved binary document images from the DFKI dataset. The figure shows the results of applying the method to extract virtual baselines from distorted document images.

- manual_score: 0
- manual_notes: Unsupported: the shown top sources do not mention Figure 6 or otherwise establish what the document's figures show. 

#### Question 15

**Question:** What is one important piece of information from the middle of the document?

**Retrieval backend:** chroma
**Retrieval time:** 0.198 s
**Generation time:** 8.604 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 1, "score": 0.4333, "vector_score": 0.4871, "lexical_score": 0.3333, "snippet": "[Página 1]\nExtraction of Virtual Baselines from Distorted Document Images\nUsing Curvilinear Projection\nGaofeng MENG∗†, Zuming HUANG†, Y onghong SONG‡,\nShiming XIANG† and Chunhong PAN†\n† National Laboratory of Pattern Recognition, Institute of Automation\nChinese Academy of Sciences, Beijing P .R.China, 100190\nEmail: {gfmeng, smxiang, chpan }@nlpr.ia.ac.cn, huangzuming2014@ia.ac.cn\n‡ Institute of Ar"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 24, "score": 0.4237, "vector_score": 0.4724, "lexical_score": 0.3333, "snippet": "tracted baselines overlapped, the edge maps and the close-up image patches, respectively. The left-most three images come\nfrom English documents and the right-most four images come from Chinese documents. The last image is a scanned book page.\nOut-of-focus blurring commonly happens to a camera-\ncaptured document image. This is because that the camera\nis hard to focus accurately on the document pag"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.4226, "vector_score": 0.4707, "lexical_score": 0.3333, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 21, "score": 0.4222, "vector_score": 0.47, "lexical_score": 0.3333, "snippet": "d baseline is further smoothed by a cubic spline.\n3. Experimental Results\nTo test the performance of the proposed method, we car-\nried out a series of experiments on a great number of curved\ndocument images. These testing images include samples of\nscanned book pages and pages captured from books, maga-\nzines and paper sheets by a hand-held camera. In the exper-\niments, we empirically set the expon"}]`

**Generated answer:**

One important piece of information from the middle of the document is that the proposed method can extract complete baselines through each pixel of document images with high accuracy, and it is script-insensitive and highly robust to image noises, non-textual objects, image resolutions, and image quality degradation like blurring and non-uniform illumination.

- manual_score: 1
- manual_notes: Partially aligned with experiment/robustness snippets, but many details are unsupported and not clearly taken from the middle of the document. 

#### Question 16

**Question:** What is one limitation, note, or important observation mentioned near the end?

**Retrieval backend:** chroma
**Retrieval time:** 0.246 s
**Generation time:** 11.861 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 32, "score": 0.333, "vector_score": 0.4046, "lexical_score": 0.2, "snippet": "nes by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Página 9]\nReferences\n[1] S. Avidan and A. Shamir. Seam carving for content-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dins"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 28, "score": 0.3251, "vector_score": 0.4463, "lexical_score": 0.1, "snippet": "specialized code optimization. The running speed may be\nfurther increased by using an image down-sampling tech-\nnique, since reduction of image resolutions will not greatly\ndecrease the accuracy of baseline extraction.\n4. Discussions and Conclusion\n4.1. Limitations\nOur method relies on the local linearity assumption of\nthe baselines. That is, the curved baselines can be well ap-\nproximated by line"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 18, "score": 0.3214, "vector_score": 0.3867, "lexical_score": 0.2, "snippet": "ects with the two vertical boundaries of a strip at A and B\nrespectively, as illustrated in Figure 4(b). The v-coordinates\nof A and B in the image coordinate system of strip can be\ncomputed respectively as:\nvA = ks− 1 − w\n2 cot θi\nks−1 , (8)\nvB = ks− 1 + w\n2 cot θi\nks−1 , (9)\nwhere w is the width of the strip.\nAs illustrated in Figure 4(b), to avoid the intersection of\nthe projection line with its"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 33, "score": 0.3154, "vector_score": 0.3776, "lexical_score": 0.2, "snippet": "e on Computer Vision (ICCV) , pages\n228–233, 2003.\n[5] E. W. Dijkstra. A note on two problems in connexion with\ngraphs. Numerische Mathematik, 1(1):269–271, 1959.\n[6] R. dos Santos, G. Clemente, T. I. Ren, and G. Cavalcanti.\nText line segmentation based on morphology and histogram\nprojection. In Proceedings of the 10th International Con-\nference on Document Analysis and Recognition , pages 651–\n65"}]`

**Generated answer:**

One limitation mentioned near the end is that the method relies on the local linearity assumption of the baselines. This means that curved baselines can be well approximated by linear segments within a narrow image strip. However, if this assumption does not hold, the method may fail, especially for document images with severe geometric distortions, such as folding distortion, where the baselines have many abrupt turnings and cannot be well approximated by linear segments without prior knowledge of the turning points.

- manual_score: 1
- manual_notes: The local-linearity limitation is supported by the end snippet, but the extra discussion of severe folding/abrupt turnings goes beyond the visible evidence.
