# PDF Extraction Benchmark Review

Generated at: 2026-03-15 01:12:42
Provider: ollama · Model: qwen2.5:7b · Prompt profile: neutral

## How to use this review file

For each question, fill in:
- `manual_score`: 0, 1, or 2
- `manual_notes`: comments about answer quality, retrieval quality, and noise

---

Review packet: 08
Document: Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf
Mode: hybrid — Híbrido inteligente · pypdf + Docling seletivo
Questions in this packet: 16

### Mode: hybrid — Híbrido inteligente · pypdf + Docling seletivo

- Extraction time: 25.295 s
- Indexing time: 5.343 s
- Final characters: 54507
- Chunks: 55
- Docling mode: selective_pages
- Suspicious pages: [1, 3, 5, 6, 8]
- Pages processed with Docling: [1, 3, 5, 6, 8]

#### Question 1

**Question:** What main problem does the paper try to solve?

**Retrieval backend:** chroma
**Retrieval time:** 0.154 s
**Generation time:** 16.152 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 8, "score": 0.4562, "vector_score": 0.5, "lexical_score": 0.375, "snippet": "e baselines of documents do not intersect with each other and that within a narrow strip, the baselines can be well approximated by linear segments. Based upon these observations, we propose a curvilinear projection based method and model the estimation of curved baselines as a constrained sequential optimization problem. A dynamic programming algorithm is then developed to efficiently solve the p"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.4551, "vector_score": 0.4983, "lexical_score": 0.375, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 12, "score": 0.4128, "vector_score": 0.5005, "lexical_score": 0.25, "snippet": "ines, spa-\ntially varying skew and irregular inter-character distance.\nIn comparison to the tracing based approaches, the methods\nusing CCs clustering are generally more robust to the curl-\ning of text lines. However, these methods often suffer from\nheuristic merging rules, artiﬁcial parameters and topologi-\ncal changes of CCs [10].\nThe segmentation based methods [19, 23, 11] treat text\nlines extr"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 11, "score": 0.4107, "vector_score": 0.4972, "lexical_score": 0.25, "snippet": "[12], where texture ﬂow is introduced for\ntracing curved text lines. However, the tracing based meth-\nods are vulnerable to page layouts, changes of font sizes and\nnon-textual image contents, leading to an inaccurate tracing\non curved text lines.\nIn most cases, it is beneﬁcial to view text lines extrac-\ntion as a clustering problem of CCs. From this perspective,\nYin and Liu [27] propose a bottom-u"}]`

**Generated answer:**

The paper tries to solve the problem of extracting the baselines of document pages, especially for documents with curved or irregular shapes. The main challenges addressed include:

1. The baselines of documents do not intersect with each other.
2. Within a narrow strip, the baselines can be well approximated by linear segments.
3. The proposed method models the estimation of curved baselines as a constrained sequential optimization problem.
4. It uses a dynamic programming algorithm to efficiently solve the problem.
5. The method can accurately extract complete baselines through each pixel of document images.
6. It is robust to various factors such as script insensitivity, image noises, non-textual objects, image resolutions, and image quality degradation like blurring and non-uniform illumination.

The overall goal is to provide a highly accurate and robust method for baseline extraction in document images, particularly for curved or irregular documents.

- manual_score: 1
- manual_notes: Partly correct on baseline extraction/curved documents, but adds many unsupported claims (pixel-level extraction, robustness details) not shown in Top sources.

#### Question 2

**Question:** What core observations motivate the proposed method?

**Retrieval backend:** chroma
**Retrieval time:** 0.508 s
**Generation time:** 8.368 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.542, "vector_score": 0.5261, "lexical_score": 0.5714, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 8, "score": 0.5412, "vector_score": 0.5249, "lexical_score": 0.5714, "snippet": "e baselines of documents do not intersect with each other and that within a narrow strip, the baselines can be well approximated by linear segments. Based upon these observations, we propose a curvilinear projection based method and model the estimation of curved baselines as a constrained sequential optimization problem. A dynamic programming algorithm is then developed to efficiently solve the p"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 45, "score": 0.5376, "vector_score": 0.5194, "lexical_score": 0.5714, "snippet": "the turning points.\nOur method also shares the common limitations of most\nprojection based methods. To estimate the baselines on an\nimage strip, it requires the available visual cues within the\nstrip to be dominant. As a result, the projection may fail if\nan image strip consists of very sparse visual cues or large\nareas of non-textual objects that have too little available in-\nformation to infer t"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 44, "score": 0.5038, "vector_score": 0.5443, "lexical_score": 0.4286, "snippet": "experiments are implemented on a\nPC with a 2.6GHz Intel(R) Core(TM) CPU and 4GB RAM.\nThe implementation codes are written in Matlab without\nspecialized code optimization. The running speed may be\nfurther increased by using an image down-sampling tech-\nnique, since reduction of image resolutions will not greatly\ndecrease the accuracy of baseline extraction.\n4. Discussions and Conclusion\n4.1. Limita"}]`

**Generated answer:**

The core observations that motivate the proposed method are:

1. The baselines of a document page do not intersect with each other.
2. Within a narrow strip, the baselines can be well approximated by linear segments.

Based on these observations, the authors propose a curvilinear projection-based method to model the estimation of curved baselines as a constrained sequential optimization problem.

- manual_score: 2
- manual_notes: Correct and directly supported by the retrieved abstract snippets: non-intersecting baselines and local linear approximation within a narrow strip.

#### Question 3

**Question:** What does Figure 1 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.169 s
**Generation time:** 9.52 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 48, "score": 0.4054, "vector_score": 0.4891, "lexical_score": 0.25, "snippet": "rating seams produced by Nikolaos and Sabine’s method, (e) the estimated baselines by Nikolaos and Sabine’s method,\n(f) the extracted baselines by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Enriquecimento visual/OCR]\n89282a\n(a)\nOAmmiamdfamdllolkiilIa"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 38, "score": 0.3966, "vector_score": 0.4756, "lexical_score": 0.25, "snippet": "tml\n[Página 6]\nFigure 6. Example results of baseline extraction from the curved document images in DFKI dataset. From top to bottom: the curved\ndocument images, the extracted virtual baselines, the projections of image along the estimated baselines, the close-up image patches.\nFigure 7. More results of baseline extraction of our method on some gray-scale images. From top to bottom are: the gray-sc"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 26, "score": 0.3961, "vector_score": 0.4748, "lexical_score": 0.25, "snippet": "performance in compar-\nison with the low-order terms, optimization on them will\nresult in an explosion in computation and storage.\n2.2.3 Optimization\nDiscretizing θ uniformly between [α, β] by a ﬁxed angle\nresolution, yields an angle sequence:\nα = θ1 < θ 2 < · · · < θ m− 1 < θ m = β. (6)\n1sk \u0010\niT\nsk\njT A\nB\nL\nsk\n1sk \u0010\n(a) (b)\n\u0016\u0016\n\u0016\u0016\u0016\nFigure 4. Construction of the weighted directed graph G. (a) only\n"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 47, "score": 0.3849, "vector_score": 0.4575, "lexical_score": 0.25, "snippet": "ocument images. These images are made by ﬁltering a clear image of\nsize 1611 × 2428 using a 75 × 75 Gaussian kernels with standard deviations σ ranging from 0 to 12 by a ﬁxed step 2. (top) the extracted\nbaselines overlapping on the blurring images, (bottom) the close-up patches for details illustration.\nFigure 9. Comparisons of our method with Koo and Cho’s method [9]. (a) the curved document imag"}]`

**Generated answer:**

The context provided does not contain any information about Figure 1. The figures mentioned are Figure 6, Figure 7, Figure 8, Figure 9, and Figure 10. If you could provide more details or clarify which figure you are referring to, I would be happy to help further.

- manual_score: 1
- manual_notes: Grounded refusal: the retrieved snippets shown do not mention Figure 1. Incomplete answer to the question, but it avoids hallucination.

#### Question 4

**Question:** What does Figure 2 illustrate?

**Retrieval backend:** chroma
**Retrieval time:** 0.263 s
**Generation time:** 4.161 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 48, "score": 0.3773, "vector_score": 0.4459, "lexical_score": 0.25, "snippet": "rating seams produced by Nikolaos and Sabine’s method, (e) the estimated baselines by Nikolaos and Sabine’s method,\n(f) the extracted baselines by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Enriquecimento visual/OCR]\n89282a\n(a)\nOAmmiamdfamdllolkiilIa"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 38, "score": 0.3674, "vector_score": 0.4306, "lexical_score": 0.25, "snippet": "tml\n[Página 6]\nFigure 6. Example results of baseline extraction from the curved document images in DFKI dataset. From top to bottom: the curved\ndocument images, the extracted virtual baselines, the projections of image along the estimated baselines, the close-up image patches.\nFigure 7. More results of baseline extraction of our method on some gray-scale images. From top to bottom are: the gray-sc"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 26, "score": 0.3672, "vector_score": 0.4303, "lexical_score": 0.25, "snippet": "performance in compar-\nison with the low-order terms, optimization on them will\nresult in an explosion in computation and storage.\n2.2.3 Optimization\nDiscretizing θ uniformly between [α, β] by a ﬁxed angle\nresolution, yields an angle sequence:\nα = θ1 < θ 2 < · · · < θ m− 1 < θ m = β. (6)\n1sk \u0010\niT\nsk\njT A\nB\nL\nsk\n1sk \u0010\n(a) (b)\n\u0016\u0016\n\u0016\u0016\u0016\nFigure 4. Construction of the weighted directed graph G. (a) only\n"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 47, "score": 0.3649, "vector_score": 0.4267, "lexical_score": 0.25, "snippet": "ocument images. These images are made by ﬁltering a clear image of\nsize 1611 × 2428 using a 75 × 75 Gaussian kernels with standard deviations σ ranging from 0 to 12 by a ﬁxed step 2. (top) the extracted\nbaselines overlapping on the blurring images, (bottom) the close-up patches for details illustration.\nFigure 9. Comparisons of our method with Koo and Cho’s method [9]. (a) the curved document imag"}]`

**Generated answer:**

Unfortunately, there is no Figure 2 mentioned or shown in the provided context. The context refers to Figures 6, 7, 8, 9, and 10, but not Figure 2. If you could provide more details or check the figure number, I would be happy to help with what that specific figure illustrates.

- manual_score: 1
- manual_notes: Grounded refusal: Top sources shown do not provide Figure 2 details. Incomplete, but conservative and supported by the visible retrieval.

#### Question 5

**Question:** What does Figure 3 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.207 s
**Generation time:** 11.353 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 48, "score": 0.3776, "vector_score": 0.4463, "lexical_score": 0.25, "snippet": "rating seams produced by Nikolaos and Sabine’s method, (e) the estimated baselines by Nikolaos and Sabine’s method,\n(f) the extracted baselines by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Enriquecimento visual/OCR]\n89282a\n(a)\nOAmmiamdfamdllolkiilIa"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 34, "score": 0.3753, "vector_score": 0.4428, "lexical_score": 0.25, "snippet": "ip. In the example, θ is uniformly discretized between 45 ◦ and 135 ◦ by an angle step 0 . 5 ◦ , and totally 30 samples of k are used to solve the path. The comparisons of strip projections along a fixed direction and the estimated baselines are also illustrated in the figure. From the results, we can see that the projections get mixed on the left side along the fixed direction. In comparison, the"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 38, "score": 0.3741, "vector_score": 0.4409, "lexical_score": 0.25, "snippet": "tml\n[Página 6]\nFigure 6. Example results of baseline extraction from the curved document images in DFKI dataset. From top to bottom: the curved\ndocument images, the extracted virtual baselines, the projections of image along the estimated baselines, the close-up image patches.\nFigure 7. More results of baseline extraction of our method on some gray-scale images. From top to bottom are: the gray-sc"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 29, "score": 0.374, "vector_score": 0.4408, "lexical_score": 0.25, "snippet": "ed between 45◦ and 135◦\nby an angle step 0.5◦ , and totally 30 samples of k are used to\nsolve the path. The comparisons of strip projections along\na ﬁxed direction and the estimated baselines are also illus-\ntrated in the ﬁgure. From the results, we can see that the\nprojections get mixed on the left side along the ﬁxed di-\nrection. In comparison, the projections along the estimated\nbaselines are m"}]`

**Generated answer:**

The information provided does not include a direct description of what Figure 3 shows. However, based on the context, Figure 5, which is described, seems to be related to the process of estimating baselines on a strip. If Figure 3 exists, it likely contains an example strip used for the baseline extraction process, similar to what Figure 5 illustrates. Figure 5 in the context shows:

- The solved optimal path (red curve) on R
- The estimated baselines on the strip
- Projection profiles of the strip along a fixed direction
- Projection profiles of the strip along the estimated baselines

For precise details about Figure 3, more specific information from the paper would be needed.

- manual_score: 0
- manual_notes: Mostly speculative: it does not answer Figure 3 and instead guesses based on Figure 5-style content. Not supported by the shown snippets.

#### Question 6

**Question:** What does Figure 5 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.508 s
**Generation time:** 12.153 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 38, "score": 0.389, "vector_score": 0.4639, "lexical_score": 0.25, "snippet": "tml\n[Página 6]\nFigure 6. Example results of baseline extraction from the curved document images in DFKI dataset. From top to bottom: the curved\ndocument images, the extracted virtual baselines, the projections of image along the estimated baselines, the close-up image patches.\nFigure 7. More results of baseline extraction of our method on some gray-scale images. From top to bottom are: the gray-sc"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 48, "score": 0.3795, "vector_score": 0.4492, "lexical_score": 0.25, "snippet": "rating seams produced by Nikolaos and Sabine’s method, (e) the estimated baselines by Nikolaos and Sabine’s method,\n(f) the extracted baselines by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Enriquecimento visual/OCR]\n89282a\n(a)\nOAmmiamdfamdllolkiilIa"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 34, "score": 0.3777, "vector_score": 0.4465, "lexical_score": 0.25, "snippet": "ip. In the example, θ is uniformly discretized between 45 ◦ and 135 ◦ by an angle step 0 . 5 ◦ , and totally 30 samples of k are used to solve the path. The comparisons of strip projections along a fixed direction and the estimated baselines are also illustrated in the figure. From the results, we can see that the projections get mixed on the left side along the fixed direction. In comparison, the"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 26, "score": 0.3767, "vector_score": 0.4449, "lexical_score": 0.25, "snippet": "performance in compar-\nison with the low-order terms, optimization on them will\nresult in an explosion in computation and storage.\n2.2.3 Optimization\nDiscretizing θ uniformly between [α, β] by a ﬁxed angle\nresolution, yields an angle sequence:\nα = θ1 < θ 2 < · · · < θ m− 1 < θ m = β. (6)\n1sk \u0010\niT\nsk\njT A\nB\nL\nsk\n1sk \u0010\n(a) (b)\n\u0016\u0016\n\u0016\u0016\u0016\nFigure 4. Construction of the weighted directed graph G. (a) only\n"}]`

**Generated answer:**

Figure 5 shows the results of the estimated baselines on a specific strip. Specifically:

- (a) illustrates the solved optimal path (represented by a red curve) on the strip.
- (b) displays the estimated baselines on the strip.
- (c) shows the projection profiles of the strip along a fixed direction.
- (d) shows the projection profiles of the strip along the estimated baselines.

From these results, it can be observed that the projections along the estimated baselines are more separable compared to those along a fixed direction, indicating better performance of the method in this aspect.

- manual_score: 1
- manual_notes: Partly correct overall idea (estimated baselines / projection comparison), but the panel-by-panel details are not explicitly supported by the shown Top sources.

#### Question 7

**Question:** At a high level, how does the curvilinear projection work?

**Retrieval backend:** chroma
**Retrieval time:** 0.261 s
**Generation time:** 13.446 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 8, "score": 0.5599, "vector_score": 0.5922, "lexical_score": 0.5, "snippet": "e baselines of documents do not intersect with each other and that within a narrow strip, the baselines can be well approximated by linear segments. Based upon these observations, we propose a curvilinear projection based method and model the estimation of curved baselines as a constrained sequential optimization problem. A dynamic programming algorithm is then developed to efficiently solve the p"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 45, "score": 0.5463, "vector_score": 0.6385, "lexical_score": 0.375, "snippet": "the turning points.\nOur method also shares the common limitations of most\nprojection based methods. To estimate the baselines on an\nimage strip, it requires the available visual cues within the\nstrip to be dominant. As a result, the projection may fail if\nan image strip consists of very sparse visual cues or large\nareas of non-textual objects that have too little available in-\nformation to infer t"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 13, "score": 0.543, "vector_score": 0.6334, "lexical_score": 0.375, "snippet": "layouts and scripts. How-\never, these methods share the similar limitations that most\nsegmentation methods may have. They are sensitive to im-\nage noises, changes of image resolutions and overlapping\nof adjacent text lines.\nThe projection based methods [20, 6, 2, 21] have been\nextensively studied to segment text lines in handwritten doc-\numents. These methods ﬁrstly compute the projection pro-\nﬁle"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 46, "score": 0.5277, "vector_score": 0.61, "lexical_score": 0.375, "snippet": "urvilinear projection is proposed to es-\ntimate the baselines.\nIn comparison with the existing approaches, the pro-\nposed method has a much low computation complexity and\ncan be implemented very efﬁciently. It is a segment-free\nmethod and can extract the complete baselines in a high ac-\ncuracy for every pixel in the image, not merely limited to\nthe baselines of textual regions. Moreover, our metho"}]`

**Generated answer:**

The curvilinear projection method works by leveraging two key observations:
1. The baselines of a document page do not intersect with each other.
2. Within a narrow vertical strip of the document image, the baselines can be well approximated by linear segments.

Based on these observations, the method models the estimation of curved baselines as a constrained sequential optimization problem. A dynamic programming algorithm is then developed to efficiently solve this problem. This approach allows the method to extract complete baselines through each pixel of the document image with high accuracy.

The method is designed to be robust to various challenges such as image noises, non-textual objects, changes in image resolution, and image quality degradation like blurring and non-uniform illumination. It is also script-insensitive and can exploit a variety of visual cues for baseline estimation, including text lines, table lines, and photo boundaries.

- manual_score: 1
- manual_notes: Core mechanism is right and grounded (observations + constrained optimization + dynamic programming), but the answer adds several unsupported robustness/details beyond the shown snippets.

#### Question 8

**Question:** Which algorithm is used to solve the optimization problem?

**Retrieval backend:** chroma
**Retrieval time:** 0.273 s
**Generation time:** 9.447 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 33, "score": 0.694, "vector_score": 0.5293, "lexical_score": 1.0, "snippet": "50\nRecognitio nand Joee\nVertrowic Enrin modebetwe\nand θ j k s , the weight on this edge, denoted by w ij s , is given as:\nSTRACT\nes of variablo w mance of our r\nDUCTION\nr. Certainiya n is performed:\nes. More recer\nNover, thoro wi\nп rastrieren up 15) at SUNY\nstormed inton ures Fetters an\nof certain fi d generato a li\nword with then iron system\n<!-- formula-not-decoded -->\nwhere p is a predefined ex"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 28, "score": 0.6771, "vector_score": 0.5032, "lexical_score": 1.0, "snippet": "− vA)2\n), cos− 1( vB − ks√\nw2\n4 + (vB − ks)2\n)\n\n .\n(10)\nIn the construction of G, every directed edge is also as-\nsigned a weight. For an edge connecting two vertices θi\nks−1\n3928\n[Página 5]\nand θj\nks\n, the weight on this edge, denoted by wij\ns , is given\nas:\nwij\ns =\n∆k∑\nt=1\nRp(ks− 1 + t, θ i\nks−1 + th)+λ∆k exp\n(\n− h2\n2σ2\n)\n,\n(11)\nwhere p is a predeﬁned exponent in Eq.(4), ∆k is the ﬁxed\ninterva"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.6193, "vector_score": 0.4912, "lexical_score": 0.8571, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 8, "score": 0.6191, "vector_score": 0.491, "lexical_score": 0.8571, "snippet": "e baselines of documents do not intersect with each other and that within a narrow strip, the baselines can be well approximated by linear segments. Based upon these observations, we propose a curvilinear projection based method and model the estimation of curved baselines as a constrained sequential optimization problem. A dynamic programming algorithm is then developed to efficiently solve the p"}]`

**Generated answer:**

The optimization problem is efficiently solved by Dijkstra's algorithm. This is mentioned in the context provided, where it states that after constructing the graph \( G \), the problem of finding an optimal path that maximizes the total sum of the weights of edges on the path can be transformed into a classic longest path problem, which can be solved by Dijkstra's algorithm.

- manual_score: 0
- manual_notes: Incorrect/unsupported. The visible Top sources say a dynamic programming algorithm is developed; Dijkstra is not supported by the shown evidence.

#### Question 9

**Question:** What are the main experimental results described in the paper?

**Retrieval backend:** chroma
**Retrieval time:** 0.278 s
**Generation time:** 21.371 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 48, "score": 0.5138, "vector_score": 0.5213, "lexical_score": 0.5, "snippet": "rating seams produced by Nikolaos and Sabine’s method, (e) the estimated baselines by Nikolaos and Sabine’s method,\n(f) the extracted baselines by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Enriquecimento visual/OCR]\n89282a\n(a)\nOAmmiamdfamdllolkiilIa"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 30, "score": 0.4912, "vector_score": 0.4864, "lexical_score": 0.5, "snippet": "a basic step is to determine the ending point of a\nbaseline giving its starting point. This can be quickly com-\nputed by using the equations of baselines in Eq.(3). Recall\nthat two neighboring strips overlap each other. We thereby\nsimply set the starting and ending points of all baselines of a\nstrip at the center lines of the overlapping areas. Finally, ev-\nery extracted baseline is further smooth"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 47, "score": 0.4831, "vector_score": 0.474, "lexical_score": 0.5, "snippet": "ocument images. These images are made by ﬁltering a clear image of\nsize 1611 × 2428 using a 75 × 75 Gaussian kernels with standard deviations σ ranging from 0 to 12 by a ﬁxed step 2. (top) the extracted\nbaselines overlapping on the blurring images, (bottom) the close-up patches for details illustration.\nFigure 9. Comparisons of our method with Koo and Cho’s method [9]. (a) the curved document imag"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 49, "score": 0.4473, "vector_score": 0.4863, "lexical_score": 0.375, "snippet": "nd Cho's method, (c) text-lines extraction and fitting by Koo and Cho's method, (d) edge maps used by our method, (e) baseline extraction by our method (totally 25 strips used), (f) the close-up image patches of results by Koo and Cho's method (top) and our method (bottom), respectively.\nFigure 10. Comparisons of our method with Tian and Narasimhan's method [25] and Nikolaos and Sabine's method [1"}]`

**Generated answer:**

The main experimental results described in the paper include comparisons of the proposed method with other methods on a series of curved document images. Specifically:

1. The paper shows results of baseline extraction on a sequence of blurred document images, comparing the extracted baselines with those produced by other methods. Figure 8 illustrates this, showing the extracted baselines overlapping on the blurred images and close-up patches for details.

2. Figure 9 compares the proposed method with Koo and Cho's method, showing:
   - Curved document images
   - Edge maps used by Koo and Cho's method
   - Text-line extraction and fitting by Koo and Cho's method
   - Edge maps used by the proposed method
   - Baseline extraction by the proposed method
   - Close-up image patches of results by Koo and Cho's method and the proposed method

3. Figure 10 compares the proposed method with Tian and Narasimhan's method and Nikolaos and Sabine's method, showing:
   - Curved images
   - Coarse estimation of baselines by Tian and Narasimhan's method
   - Refinement results of Tian and Narasimhan's method
   - Separating seams produced by Nikolaos and Sabine's method
   - Estimated baselines by Nikolaos and Sabine's method
   - Extracted baselines by the proposed method

These comparisons help to demonstrate the effectiveness and performance of the proposed method in extracting baselines from curved document images.

- manual_score: 2
- manual_notes: Good summary of the experimental comparisons visible in the retrieved snippets: blurred-image robustness and comparisons with prior methods in Figures 9 and 10.

#### Question 10

**Question:** According to the paper, what kinds of robustness does the method demonstrate?

**Retrieval backend:** chroma
**Retrieval time:** 0.394 s
**Generation time:** 12.993 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 40, "score": 0.4651, "vector_score": 0.5361, "lexical_score": 0.3333, "snippet": "eline extraction of our method on some gray-scale images. From top to bottom are: the gray-scale images with the extracted baselines overlapped, the edge maps and the close-up image patches, respectively. The left-most three images come from English documents and the right-most four images come from Chinese documents. The last image is a scanned book page.\n<!-- image -->\nOut-of-focus blurring comm"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 39, "score": 0.4634, "vector_score": 0.5335, "lexical_score": 0.3333, "snippet": "aus-\nsian kernels. Figure 8 shows the results of baseline extrac-\ntion on these images. As can be seen from the results, our\nmethod yields comparably stable results for the images with\ndifferent levels of blurring. This demonstrates that the pro-\nposed method is quite robust to image blurring. Since im-\nage down-sampling will result in a similar blurring, this also\nmeans that the proposed method i"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 48, "score": 0.4618, "vector_score": 0.531, "lexical_score": 0.3333, "snippet": "rating seams produced by Nikolaos and Sabine’s method, (e) the estimated baselines by Nikolaos and Sabine’s method,\n(f) the extracted baselines by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Enriquecimento visual/OCR]\n89282a\n(a)\nOAmmiamdfamdllolkiilIa"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 41, "score": 0.4547, "vector_score": 0.5201, "lexical_score": 0.3333, "snippet": "e image down-sampling will result in a similar blurring, this also means that the proposed method is not sensitive to changes of image resolutions. The robustness to image blurring will benefit the process of image noise removal, since we can choose a larger kernel for image smoothing without signif-\n03-47)\n38-10 г\nBi Si2g\n[Página 7]\nicantly losing the accuracy in baseline extraction. The ro-\nbust"}]`

**Generated answer:**

According to the paper, the method demonstrates robustness to:

1. Image blurring: The method yields stable results for images with different levels of blurring, as tested by filtering a clear document image with various Gaussian kernels. This robustness to blurring also indicates insensitivity to image down-sampling, which can cause similar blurring effects.

2. Image resolutions: The method is not sensitive to changes in image resolutions, as down-sampling images results in a similar blurring effect.

These robustness properties are beneficial for image noise removal, as the method can use larger smoothing kernels without losing accuracy in baseline extraction. Additionally, the method is insensitive to touched neighboring characters and text lines, which are common in curved document images captured by hand-held cameras.

- manual_score: 1
- manual_notes: Partly correct: robustness to image blurring and resolution changes is supported. The added claim about touched neighboring characters/text lines is not visible in Top sources.

#### Question 11

**Question:** What is the central topic of the document?

**Retrieval backend:** chroma
**Retrieval time:** 0.353 s
**Generation time:** 8.277 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.4489, "vector_score": 0.4752, "lexical_score": 0.4, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 1, "score": 0.4475, "vector_score": 0.4731, "lexical_score": 0.4, "snippet": "[Página 1]\nExtraction of Virtual Baselines from Distorted Document Images\nUsing Curvilinear Projection\nGaofeng MENG∗†, Zuming HUANG†, Y onghong SONG‡,\nShiming XIANG† and Chunhong PAN†\n† National Laboratory of Pattern Recognition, Institute of Automation\nChinese Academy of Sciences, Beijing P .R.China, 100190\nEmail: {gfmeng, smxiang, chpan }@nlpr.ia.ac.cn, huangzuming2014@ia.ac.cn\n‡ Institute of Ar"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 8, "score": 0.4474, "vector_score": 0.4729, "lexical_score": 0.4, "snippet": "e baselines of documents do not intersect with each other and that within a narrow strip, the baselines can be well approximated by linear segments. Based upon these observations, we propose a curvilinear projection based method and model the estimation of curved baselines as a constrained sequential optimization problem. A dynamic programming algorithm is then developed to efficiently solve the p"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 50, "score": 0.4457, "vector_score": 0.4703, "lexical_score": 0.4, "snippet": "ent-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dinstein. Line seg-\nmentation for degraded handwritten historical documents. In\nProceedings of the 10th International Conference on Doc-\nument Analysis and Recognition , pages 1161–1165, July\n2009.\n[3] S. Bukhari, F. Shafait, and T. Breuel. Text-line extraction\nusing a convo"}]`

**Generated answer:**

The central topic of the document is the extraction of virtual baselines from curved document images using a curvilinear projection-based method. The document describes an efficient method for accurately extracting these baselines, which is crucial for the geometric correction of curved document images.

- manual_score: 2
- manual_notes: Correct and well grounded by the title and abstract snippets: extraction of virtual baselines from distorted/curved document images using curvilinear projection.

#### Question 12

**Question:** What are the 3 most important sections or takeaways?

**Retrieval backend:** chroma
**Retrieval time:** 0.247 s
**Generation time:** 20.589 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 11, "score": 0.4177, "vector_score": 0.4118, "lexical_score": 0.4286, "snippet": "[12], where texture ﬂow is introduced for\ntracing curved text lines. However, the tracing based meth-\nods are vulnerable to page layouts, changes of font sizes and\nnon-textual image contents, leading to an inaccurate tracing\non curved text lines.\nIn most cases, it is beneﬁcial to view text lines extrac-\ntion as a clustering problem of CCs. From this perspective,\nYin and Liu [27] propose a bottom-u"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 12, "score": 0.4167, "vector_score": 0.4103, "lexical_score": 0.4286, "snippet": "ines, spa-\ntially varying skew and irregular inter-character distance.\nIn comparison to the tracing based approaches, the methods\nusing CCs clustering are generally more robust to the curl-\ning of text lines. However, these methods often suffer from\nheuristic merging rules, artiﬁcial parameters and topologi-\ncal changes of CCs [10].\nThe segmentation based methods [19, 23, 11] treat text\nlines extr"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 10, "score": 0.3872, "vector_score": 0.4418, "lexical_score": 0.2857, "snippet": "3, 4, 24, 25], the\nclustering based methods [9, 10, 22, 27], the segmentation\nbased methods [11, 19, 23] and the projection based meth-\nods [20, 26, 2, 21].\nEarly methods for text lines extraction apply a tracing\nstrategy to the connected components (CCs) of a binarized\nimage [4, 16, 24]. These methods ﬁrstly pick up a con-\nnected component from the image as a seed, then perform\nseed growing by li"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 9, "score": 0.3767, "vector_score": 0.4257, "lexical_score": 0.2857, "snippet": "nserted photos, are aligned. Many methods for document image anal-\n[Página 2]\nbound book by a hand-held camera.\nThe extraction of baselines is of great importance to\nmany methods for the rectiﬁcation of geometric distortion\nin camera-captured document images [4, 28, 7, 8, 12, 13,\n15, 16, 24]. To yield a desirable result, these methods re-\nquire the curved baselines to be estimated reliably in a hi"}]`

**Generated answer:**

Based on the provided context, here are three important sections or takeaways:

1. **Text Line Extraction Methods**:
   - **Tracing-Based Methods**: These methods involve tracing connected components (CCs) of a binarized image. They are scripts-sensitive and unstable, especially for characters with multiple components like Chinese characters. They are vulnerable to page layouts, font size changes, and non-textual image contents.
   - **Clustering-Based Methods**: These methods treat text line extraction as a clustering problem of CCs. They are generally more robust to the curling of text lines but often suffer from heuristic merging rules, artificial parameters, and topological changes of CCs.
   - **Segmentation-Based Methods**: These methods treat text line extraction as an image segmentation problem. They are more general-purpose and require less knowledge about document layouts and scripts but are sensitive to image noises, changes in image resolutions, and overlapping text lines.

2. **Challenges in Baseline Extraction**:
   - Extracting baselines is crucial for rectifying geometric distortion in camera-captured document images. However, this is challenging due to image distortion, non-textual objects, and image quality degradation (e.g., blurring, low resolution, non-uniform illumination).

3. **Categories of Text Line Extraction Methods**:
   - The methods can be categorized into four main types: tracing-based, clustering-based, segmentation-based, and projection-based. Each category has its strengths and weaknesses, making them suitable for different scenarios and challenges in text line extraction.

- manual_score: 1
- manual_notes: Partly grounded in the related-work snippets, but it over-focuses on prior method categories and misses stronger document takeaways about the proposed method/results.

#### Question 13

**Question:** Does the document contain tables? What do they show?

**Retrieval backend:** chroma
**Retrieval time:** 0.324 s
**Generation time:** 9.141 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 37, "score": 0.522, "vector_score": 0.5338, "lexical_score": 0.5, "snippet": "well exploit the available visual cues, such as text lines, horizontal lines in tables and page boundaries, to infer the baselines in the blank areas and non-textual regions.\nWe also give more results of our method on gray-scale document images in Figure 7. These images include pages captured by a hand-held camera or scanned by a flat-bed scanner from books, magazines and paper sheets. Note that s"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 1, "score": 0.4817, "vector_score": 0.5391, "lexical_score": 0.375, "snippet": "[Página 1]\nExtraction of Virtual Baselines from Distorted Document Images\nUsing Curvilinear Projection\nGaofeng MENG∗†, Zuming HUANG†, Y onghong SONG‡,\nShiming XIANG† and Chunhong PAN†\n† National Laboratory of Pattern Recognition, Institute of Automation\nChinese Academy of Sciences, Beijing P .R.China, 100190\nEmail: {gfmeng, smxiang, chpan }@nlpr.ia.ac.cn, huangzuming2014@ia.ac.cn\n‡ Institute of Ar"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.4696, "vector_score": 0.5206, "lexical_score": 0.375, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 38, "score": 0.4325, "vector_score": 0.5307, "lexical_score": 0.25, "snippet": "tml\n[Página 6]\nFigure 6. Example results of baseline extraction from the curved document images in DFKI dataset. From top to bottom: the curved\ndocument images, the extracted virtual baselines, the projections of image along the estimated baselines, the close-up image patches.\nFigure 7. More results of baseline extraction of our method on some gray-scale images. From top to bottom are: the gray-sc"}]`

**Generated answer:**

The document mentions the use of "text lines, horizontal lines in tables and page boundaries" as visual cues for inferring baselines. However, it does not explicitly state that the document contains tables or provide details about what tables show. The focus seems to be on using various visual elements to extract baselines from curved document images, but specific information about tables is not provided in the given context.

- manual_score: 1
- manual_notes: Conservative and grounded: the shown snippets mention table lines as cues, but do not clearly show actual tables or what any table contains.

#### Question 14

**Question:** Does the document contain figures or diagrams? What do they show?

**Retrieval backend:** chroma
**Retrieval time:** 0.219 s
**Generation time:** 19.389 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 37, "score": 0.4625, "vector_score": 0.5321, "lexical_score": 0.3333, "snippet": "well exploit the available visual cues, such as text lines, horizontal lines in tables and page boundaries, to infer the baselines in the blank areas and non-textual regions.\nWe also give more results of our method on gray-scale document images in Figure 7. These images include pages captured by a hand-held camera or scanned by a flat-bed scanner from books, magazines and paper sheets. Note that s"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 48, "score": 0.4358, "vector_score": 0.5508, "lexical_score": 0.2222, "snippet": "rating seams produced by Nikolaos and Sabine’s method, (e) the estimated baselines by Nikolaos and Sabine’s method,\n(f) the extracted baselines by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Enriquecimento visual/OCR]\n89282a\n(a)\nOAmmiamdfamdllolkiilIa"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 38, "score": 0.433, "vector_score": 0.5465, "lexical_score": 0.2222, "snippet": "tml\n[Página 6]\nFigure 6. Example results of baseline extraction from the curved document images in DFKI dataset. From top to bottom: the curved\ndocument images, the extracted virtual baselines, the projections of image along the estimated baselines, the close-up image patches.\nFigure 7. More results of baseline extraction of our method on some gray-scale images. From top to bottom are: the gray-sc"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 7, "score": 0.4294, "vector_score": 0.5409, "lexical_score": 0.2222, "snippet": "ument image processing and analysis, such as page layout segmentation, optical character recognition (OCR) and so on.\nFor a flat document image, its baselines are usually straight lines. The estimation of these baselines has been extensively studied in the context of document image deskewing [17] and image perspective rectification [14, 22]. The problem, however, gets worse when a document image i"}]`

**Generated answer:**

Yes, the document contains several figures and diagrams. Here's a summary of what they show:

1. **Figure 6**: Shows example results of baseline extraction from curved document images in the DFKI dataset. It includes:
   - Curved document images.
   - Extracted virtual baselines.
   - Projections of the image along the estimated baselines.
   - Close-up image patches.

2. **Figure 7**: Displays more results of baseline extraction on gray-scale images. It includes:
   - Gray-scale images with extracted baselines overlapped.
   - Edge maps.
   - Close-up image patches.
   - The left-most three images are from English documents, and the right-most four are from Chinese documents.

3. **Figure 8**: Illustrates the results of baseline extraction on a sequence of blurred document images. It includes:
   - Blurred images.
   - Extracted baselines overlapping on the blurred images.
   - Close-up patches for details.

4. **Figure 9**: Compares the method with Koo and Cho's method. It includes:
   - Curved document images.
   - Edge maps used by Koo and Cho's method.
   - Text-line extraction and fitting by Koo and Cho's method.
   - Edge maps used by the proposed method.
   - Baseline extraction by the proposed method.
   - A close-up image.

These figures help visualize the effectiveness of the proposed method in extracting baselines from various types of document images, including curved, gray-scale, and blurred images.

- manual_score: 1
- manual_notes: Partly correct that the document contains figures, but the answer mixes in figure details not clearly supported by the shown Top sources for this question.

#### Question 15

**Question:** What is one important piece of information from the middle of the document?

**Retrieval backend:** chroma
**Retrieval time:** 0.357 s
**Generation time:** 8.724 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 7, "score": 0.4761, "vector_score": 0.4931, "lexical_score": 0.4444, "snippet": "ument image processing and analysis, such as page layout segmentation, optical character recognition (OCR) and so on.\nFor a flat document image, its baselines are usually straight lines. The estimation of these baselines has been extensively studied in the context of document image deskewing [17] and image perspective rectification [14, 22]. The problem, however, gets worse when a document image i"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 48, "score": 0.4366, "vector_score": 0.4923, "lexical_score": 0.3333, "snippet": "rating seams produced by Nikolaos and Sabine’s method, (e) the estimated baselines by Nikolaos and Sabine’s method,\n(f) the extracted baselines by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Enriquecimento visual/OCR]\n89282a\n(a)\nOAmmiamdfamdllolkiilIa"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 1, "score": 0.4333, "vector_score": 0.4871, "lexical_score": 0.3333, "snippet": "[Página 1]\nExtraction of Virtual Baselines from Distorted Document Images\nUsing Curvilinear Projection\nGaofeng MENG∗†, Zuming HUANG†, Y onghong SONG‡,\nShiming XIANG† and Chunhong PAN†\n† National Laboratory of Pattern Recognition, Institute of Automation\nChinese Academy of Sciences, Beijing P .R.China, 100190\nEmail: {gfmeng, smxiang, chpan }@nlpr.ia.ac.cn, huangzuming2014@ia.ac.cn\n‡ Institute of Ar"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 38, "score": 0.4305, "vector_score": 0.4829, "lexical_score": 0.3333, "snippet": "tml\n[Página 6]\nFigure 6. Example results of baseline extraction from the curved document images in DFKI dataset. From top to bottom: the curved\ndocument images, the extracted virtual baselines, the projections of image along the estimated baselines, the close-up image patches.\nFigure 7. More results of baseline extraction of our method on some gray-scale images. From top to bottom are: the gray-sc"}]`

**Generated answer:**

One important piece of information from the middle of the document is that the baselines of a document page are a set of virtual horizontal and parallel lines, to which the printed contents such as text lines, tables, or inserted photos are aligned. Accurate baseline extraction is crucial for the geometric correction of curved document images.

- manual_score: 0
- manual_notes: Weakly grounded and not clearly from the middle of the document. The specific statement is not supported by the visible Top sources.

#### Question 16

**Question:** What is one limitation, note, or important observation mentioned near the end?

**Retrieval backend:** chroma
**Retrieval time:** 0.3 s
**Generation time:** 11.024 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 50, "score": 0.3321, "vector_score": 0.4032, "lexical_score": 0.2, "snippet": "ent-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dinstein. Line seg-\nmentation for degraded handwritten historical documents. In\nProceedings of the 10th International Conference on Doc-\nument Analysis and Recognition , pages 1161–1165, July\n2009.\n[3] S. Bukhari, F. Shafait, and T. Breuel. Text-line extraction\nusing a convo"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 44, "score": 0.3165, "vector_score": 0.4331, "lexical_score": 0.1, "snippet": "experiments are implemented on a\nPC with a 2.6GHz Intel(R) Core(TM) CPU and 4GB RAM.\nThe implementation codes are written in Matlab without\nspecialized code optimization. The running speed may be\nfurther increased by using an image down-sampling tech-\nnique, since reduction of image resolutions will not greatly\ndecrease the accuracy of baseline extraction.\n4. Discussions and Conclusion\n4.1. Limita"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 48, "score": 0.3019, "vector_score": 0.4106, "lexical_score": 0.1, "snippet": "rating seams produced by Nikolaos and Sabine’s method, (e) the estimated baselines by Nikolaos and Sabine’s method,\n(f) the extracted baselines by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natural Science Founda-\ntion of China (Grant No. 61370039, 61272331, 91338202).\n3932\n[Enriquecimento visual/OCR]\n89282a\n(a)\nOAmmiamdfamdllolkiilIa"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 11, "score": 0.2978, "vector_score": 0.4043, "lexical_score": 0.1, "snippet": "[12], where texture ﬂow is introduced for\ntracing curved text lines. However, the tracing based meth-\nods are vulnerable to page layouts, changes of font sizes and\nnon-textual image contents, leading to an inaccurate tracing\non curved text lines.\nIn most cases, it is beneﬁcial to view text lines extrac-\ntion as a clustering problem of CCs. From this perspective,\nYin and Liu [27] propose a bottom-u"}]`

**Generated answer:**

One limitation mentioned near the end is that the method relies on the local linearity assumption of the baselines. This means that curved baselines can be well approximated by linear segments within a narrow image strip. However, if this assumption does not hold, the method may fail, particularly for document images with severe geometric distortions, such as folding distortion, where the baselines have many abrupt turnings and cannot be well approximated by linear segments without prior knowledge of the turning points.

- manual_score: 0
- manual_notes: Unsupported by the shown snippets. The visible Top sources near the end do not show this limitation explicitly, so the answer goes beyond the available evidence.