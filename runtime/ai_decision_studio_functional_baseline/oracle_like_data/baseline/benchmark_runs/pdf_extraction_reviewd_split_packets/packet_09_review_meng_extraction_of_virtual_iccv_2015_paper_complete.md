# PDF Extraction Benchmark Review

Generated at: 2026-03-15 01:12:42
Provider: ollama · Model: qwen2.5:7b · Prompt profile: neutral

## How to use this review file

For each question, fill in:
- `manual_score`: 0, 1, or 2
- `manual_notes`: comments about answer quality, retrieval quality, and noise

---

Review packet: 09
Document: Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf
Mode: complete — Completo por página · cobertura máxima com Docling/OCR
Questions in this packet: 16

### Mode: complete — Completo por página · cobertura máxima com Docling/OCR

- Extraction time: 135.938 s
- Indexing time: 7.316 s
- Final characters: 74250
- Chunks: 75
- Docling mode: page_complete
- Suspicious pages: [1, 3, 5, 6, 8]
- Pages processed with Docling: [1, 2, 3, 4, 5, 6, 7, 8, 9]

#### Question 1

**Question:** What main problem does the paper try to solve?

**Retrieval backend:** chroma
**Retrieval time:** 0.155 s
**Generation time:** 16.137 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 7, "score": 0.4674, "vector_score": 0.5171, "lexical_score": 0.375, "snippet": "to efficiently solve the problem. The proposed method can extract the complete baselines through each pixel of document images in a high accuracy. It is also scripts insensitive and highly robust to image noises, non-textual objects, image resolutions and image quality degradation like blurring and non-uniform illumination. Extensive experiments on a number of captured document images demonstrate "}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.4551, "vector_score": 0.4983, "lexical_score": 0.375, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 41, "score": 0.4483, "vector_score": 0.4878, "lexical_score": 0.375, "snippet": "ataset can be downloaded from http://www.csse.uwa.\nedu.au/˜shafait/downloads.html\n3929\n[Extração completa Docling/OCR]\nand Ok, the weight on this edge, denoted by wij, is given\n<!-- formula-not-decoded -->\nwhere p is a predefined exponent in Eq.(4), Ak is the fixed interval in Eq.(7) for sampling k and\n<!-- formula-not-decoded -->\nAfter G' is constructed, the optimization of Eq.(4) turns out to be"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 64, "score": 0.4168, "vector_score": 0.5066, "lexical_score": 0.25, "snippet": "roving this paper. This work was supported in part by the projects of the National Natural Science Founda- tion of China (Grant No. 61370039, 61272331, 91338202).\n[Página 9]\nReferences\n[1] S. Avidan and A. Shamir. Seam carving for content-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dinstein. Line seg-\nmentation for degrad"}]`

**Generated answer:**

The paper tries to solve the problem of extracting the complete baselines from document images, especially when the baselines are curved. The baselines are virtual horizontal and parallel lines to which the printed contents of the document (e.g., text lines, tables, or inserted photos) are aligned. The main challenge addressed is accurately estimating these curved baselines in the presence of image distortions, various non-textual objects, and image quality degradations such as blurring and non-uniform illumination.

- manual_score: 2
- manual_notes: Correct overall and largely supported by the retrieved snippets about extracting complete curved baselines robustly; adds a bit of extra baseline-definition detail not clearly shown in Top sources.

#### Question 2

**Question:** What core observations motivate the proposed method?

**Retrieval backend:** chroma
**Retrieval time:** 0.63 s
**Generation time:** 8.304 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 54, "score": 0.5448, "vector_score": 0.5304, "lexical_score": 0.5714, "snippet": "ally occurs to page margins, where insufﬁcient cues\nare available for the correct estimation of baselines.\n4.2. Conclusion\nWe have proposed a curvilinear projection based method\nin this paper for virtual baseline extraction from a curved\nimage of printed documents. Our method is motivated from\ntwo basic observations that the baselines of a curved doc-\nument image do not intersect with each other a"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.542, "vector_score": 0.5261, "lexical_score": 0.5714, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 10, "score": 0.49, "vector_score": 0.5231, "lexical_score": 0.4286, "snippet": "u [27] propose a bottom-up method for text lines\nsegmentation in unconstrained handwritten Chinese docu-\nments. The method ﬁrst designs a distance metric between\nCCs by supervised learning. Based upon it, CCs of the doc-\nument image are grouped into a tree structure, from which\ntext lines can be extracted by dynamically cutting the edges.\nKoo and Cho [9, 10] formulate text lines extraction as an\ne"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 40, "score": 0.4847, "vector_score": 0.5149, "lexical_score": 0.4286, "snippet": "s inserted formulas\nand photos. This is mainly because the proposed method\ncan well exploit the available visual cues, such as text lines,\nhorizontal lines in tables and page boundaries, to infer the\nbaselines in the blank areas and non-textual regions.\nWe also give more results of our method on gray-scale\ndocument images in Figure 7. These images include pages\ncaptured by a hand-held camera or sc"}]`

**Generated answer:**

The core observations that motivate the proposed method are:

1. The baselines of a curved document image do not intersect with each other.
2. Within a narrow strip, the baselines can be well approximated by linear segments.

These observations form the basis for the curvilinear projection based method described in the paper.

- manual_score: 2
- manual_notes: Correct and directly supported by the snippets stating the two motivating observations: non-intersecting baselines and local linear approximation within a narrow strip.

#### Question 3

**Question:** What does Figure 1 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.294 s
**Generation time:** 9.283 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 63, "score": 0.4135, "vector_score": 0.5015, "lexical_score": 0.25, "snippet": "t images.<end_of_utteranc\nFigure 9. Comparisons of our method with Koo and Cho's method [9]. (a) the curved document images, (b) edge maps used by Koo and Cho's method, (c) text-lines extraction and fitting by Koo and Cho's method, (d) edge maps used by our method, (e) baseline extraction by our method (totally 25 strips used), (f) the close-up image patches of results by Koo and Cho's method (top"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 61, "score": 0.4003, "vector_score": 0.4813, "lexical_score": 0.25, "snippet": "iewers and area chairs for their valuable remarks and sugges-\n[Página 8]\nFigure 8. Results of baseline extraction on a sequence of blurring document images. These images are made by ﬁltering a clear image of\nsize 1611 × 2428 using a 75 × 75 Gaussian kernels with standard deviations σ ranging from 0 to 12 by a ﬁxed step 2. (top) the extracted\nbaselines overlapping on the blurring images, (bottom) t"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 62, "score": 0.3997, "vector_score": 0.4803, "lexical_score": 0.25, "snippet": ") the coarse estimation of baselines by Tian and Narasimhan’s method, (c) the reﬁnement results of Tian and Narasimhan’s\nmethod, (d) the separating seams produced by Nikolaos and Sabine’s method, (e) the estimated baselines by Nikolaos and Sabine’s method,\n(f) the extracted baselines by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natur"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 31, "score": 0.3968, "vector_score": 0.4758, "lexical_score": 0.25, "snippet": "ed in Figure 4(a). Each vertex locates at the grid point\n(ks, θj)(1 ≤ s ≤ n, 1 ≤ j ≤ m). In the graph G, only\npoints that have adjacent k-coordinates can be connected\nby a directed edge. Two points (ks− 1, θi) and (ks, θj) are\nconnected if and only if their corresponding projection lines\nsatisfy the non-intersection condition.\nFor shortness, we rewrite θi of vertex (ks− 1, θi) as θi\nks−1\nand furth"}]`

**Generated answer:**

The provided context does not contain a description of Figure 1. The context mainly discusses Figures 8, 9, and 10, but does not mention Figure 1. Therefore, I cannot provide information about what Figure 1 shows based on the given information.

- manual_score: 2
- manual_notes: Good conservative answer. The retrieved snippets do not mention Figure 1, and the model avoids hallucinating a caption.

#### Question 4

**Question:** What does Figure 2 illustrate?

**Retrieval backend:** chroma
**Retrieval time:** 0.245 s
**Generation time:** 4.519 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 63, "score": 0.3932, "vector_score": 0.4703, "lexical_score": 0.25, "snippet": "t images.<end_of_utteranc\nFigure 9. Comparisons of our method with Koo and Cho's method [9]. (a) the curved document images, (b) edge maps used by Koo and Cho's method, (c) text-lines extraction and fitting by Koo and Cho's method, (d) edge maps used by our method, (e) baseline extraction by our method (totally 25 strips used), (f) the close-up image patches of results by Koo and Cho's method (top"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 61, "score": 0.3725, "vector_score": 0.4385, "lexical_score": 0.25, "snippet": "iewers and area chairs for their valuable remarks and sugges-\n[Página 8]\nFigure 8. Results of baseline extraction on a sequence of blurring document images. These images are made by ﬁltering a clear image of\nsize 1611 × 2428 using a 75 × 75 Gaussian kernels with standard deviations σ ranging from 0 to 12 by a ﬁxed step 2. (top) the extracted\nbaselines overlapping on the blurring images, (bottom) t"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 62, "score": 0.3712, "vector_score": 0.4365, "lexical_score": 0.25, "snippet": ") the coarse estimation of baselines by Tian and Narasimhan’s method, (c) the reﬁnement results of Tian and Narasimhan’s\nmethod, (d) the separating seams produced by Nikolaos and Sabine’s method, (e) the estimated baselines by Nikolaos and Sabine’s method,\n(f) the extracted baselines by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natur"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 30, "score": 0.3656, "vector_score": 0.4279, "lexical_score": 0.25, "snippet": "to the angle differences. Similarly, high-order smooth-\nness term that involves more adjacent angles can also be\ndeﬁned. However, it has to be pointed out that although\nhigh-order terms may have better performance in compar-\nison with the low-order terms, optimization on them will\nresult in an explosion in computation and storage.\n2.2.3 Optimization\nDiscretizing θ uniformly between [α, β] by a ﬁxe"}]`

**Generated answer:**

The provided context does not contain any information about Figure 2. The context mentions Figures 4, 8, 9, and 10, but Figure 2 is not referenced. Therefore, I cannot provide what Figure 2 illustrates based on the given information.

- manual_score: 2
- manual_notes: Good conservative answer. Top sources do not provide Figure 2 information, so saying the evidence is insufficient is appropriate and grounded.

#### Question 5

**Question:** What does Figure 3 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.19 s
**Generation time:** 11.628 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 63, "score": 0.3935, "vector_score": 0.4708, "lexical_score": 0.25, "snippet": "t images.<end_of_utteranc\nFigure 9. Comparisons of our method with Koo and Cho's method [9]. (a) the curved document images, (b) edge maps used by Koo and Cho's method, (c) text-lines extraction and fitting by Koo and Cho's method, (d) edge maps used by our method, (e) baseline extraction by our method (totally 25 strips used), (f) the close-up image patches of results by Koo and Cho's method (top"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 37, "score": 0.3846, "vector_score": 0.4571, "lexical_score": 0.25, "snippet": "trated an example of the solved optimal\npath on R and the estimated baselines of the strip. In the\nexample, θ is uniformly discretized between 45◦ and 135◦\nby an angle step 0.5◦ , and totally 30 samples of k are used to\nsolve the path. The comparisons of strip projections along\na ﬁxed direction and the estimated baselines are also illus-\ntrated in the ﬁgure. From the results, we can see that the\np"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 42, "score": 0.3845, "vector_score": 0.4569, "lexical_score": 0.25, "snippet": "ip projections along a fixed direction and the estimated baselines are also illustrated in the figure. From the results, we can see that the projections get mixed on the left side along the fixed direction. In comparison, the projections along the estimated baselines are much better in separability.\nThe image is a graph showing the distribution of data points. The graph is titled \"150\" and is labe"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 43, "score": 0.3842, "vector_score": 0.4564, "lexical_score": 0.25, "snippet": "abeled as \"150\" o\nFigure 5. Results of the estimated baselines on the strip in Figure 3(a). (a) the solved optimal path (red curve) on R, (b) the estimated baselines on the strip, (c) the projection profiles of strip along a fixed direction, (d) the projection profiles of strip along the\n<!-- image -->\n## 2.3. Baselines Connection Between Strips\nAfter the baselines on each strip are estimated, we "}]`

**Generated answer:**

The information provided does not include a direct description of what Figure 3 shows. However, based on the context, Figure 5 is described in detail, which might be related to Figure 3 as it discusses strip projections and estimated baselines. 

From the context, Figure 5 shows:
- The solved optimal path (red curve) on R
- The estimated baselines on the strip
- The projection profiles of the strip along a fixed direction
- The projection profiles of the strip along the estimated baselines

If Figure 3 is similar or related to Figure 5, it likely shows a strip with its optimal path and estimated baselines, along with projection profiles. For precise details about Figure 3, we would need additional information from the paper.

- manual_score: 0
- manual_notes: Mostly unsupported. It admits Figure 3 is not described, then speculates based on Figure 5 and guesses what Figure 3 'likely' shows.

#### Question 6

**Question:** What does Figure 5 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.296 s
**Generation time:** 5.408 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 63, "score": 0.3966, "vector_score": 0.4755, "lexical_score": 0.25, "snippet": "t images.<end_of_utteranc\nFigure 9. Comparisons of our method with Koo and Cho's method [9]. (a) the curved document images, (b) edge maps used by Koo and Cho's method, (c) text-lines extraction and fitting by Koo and Cho's method, (d) edge maps used by our method, (e) baseline extraction by our method (totally 25 strips used), (f) the close-up image patches of results by Koo and Cho's method (top"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 37, "score": 0.3902, "vector_score": 0.4657, "lexical_score": 0.25, "snippet": "trated an example of the solved optimal\npath on R and the estimated baselines of the strip. In the\nexample, θ is uniformly discretized between 45◦ and 135◦\nby an angle step 0.5◦ , and totally 30 samples of k are used to\nsolve the path. The comparisons of strip projections along\na ﬁxed direction and the estimated baselines are also illus-\ntrated in the ﬁgure. From the results, we can see that the\np"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 42, "score": 0.3893, "vector_score": 0.4643, "lexical_score": 0.25, "snippet": "ip projections along a fixed direction and the estimated baselines are also illustrated in the figure. From the results, we can see that the projections get mixed on the left side along the fixed direction. In comparison, the projections along the estimated baselines are much better in separability.\nThe image is a graph showing the distribution of data points. The graph is titled \"150\" and is labe"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 43, "score": 0.3794, "vector_score": 0.4491, "lexical_score": 0.25, "snippet": "abeled as \"150\" o\nFigure 5. Results of the estimated baselines on the strip in Figure 3(a). (a) the solved optimal path (red curve) on R, (b) the estimated baselines on the strip, (c) the projection profiles of strip along a fixed direction, (d) the projection profiles of strip along the\n<!-- image -->\n## 2.3. Baselines Connection Between Strips\nAfter the baselines on each strip are estimated, we "}]`

**Generated answer:**

Figure 5 shows the results of the estimated baselines on a strip. Specifically, it includes:

- (a) The solved optimal path (red curve) on R.
- (b) The estimated baselines on the strip.
- (c) The projection profiles of the strip along a fixed direction.
- (d) The projection profiles of the strip along the estimated baselines.

From these, it is noted that the projections along the estimated baselines are much better in separability compared to those along a fixed direction.

- manual_score: 2
- manual_notes: Correct and well grounded in the retrieved Figure 5 caption/snippets; accurately lists the subpanels and main takeaway about better separability.

#### Question 7

**Question:** At a high level, how does the curvilinear projection work?

**Retrieval backend:** chroma
**Retrieval time:** 0.235 s
**Generation time:** 11.0 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 54, "score": 0.5924, "vector_score": 0.6422, "lexical_score": 0.5, "snippet": "ally occurs to page margins, where insufﬁcient cues\nare available for the correct estimation of baselines.\n4.2. Conclusion\nWe have proposed a curvilinear projection based method\nin this paper for virtual baseline extraction from a curved\nimage of printed documents. Our method is motivated from\ntwo basic observations that the baselines of a curved doc-\nument image do not intersect with each other a"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 53, "score": 0.5836, "vector_score": 0.6286, "lexical_score": 0.5, "snippet": "ssumption of\nthe baselines. That is, the curved baselines can be well ap-\nproximated by linear segments within a narrow image strip.\nHowever, if this assumption does not hold, the method may\nfail. This commonly happens to the captured document im-\nages with severe geometric distortions. Due to this reason,\nthe method cannot be applied to the document images with\nnon-smooth distortion, for example,"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 60, "score": 0.5584, "vector_score": 0.5899, "lexical_score": 0.5, "snippet": "r and that in a narrow image strip, the baselines can be well approximated by straight line segments. Based on these observations, a constrained optimal curvilinear projection is proposed to estimate the baselines.\nIn comparison with the existing approaches, the proposed method has a much low computation complexity and can be implemented very efficiently. It is a segment-free method and can extrac"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 59, "score": 0.54, "vector_score": 0.6289, "lexical_score": 0.375, "snippet": "le, folding distortion, in which the baselines have many abrupt turnings and cannot be well approximated by linear segments without any prior knowledge of the turning points.\nOur method also shares the common limitations of most projection based methods. To estimate the baselines on an image strip, it requires the available visual cues within the strip to be dominant. As a result, the projection m"}]`

**Generated answer:**

The curvilinear projection method works by leveraging two key observations:
1. The baselines of a curved document image do not intersect with each other.
2. In a narrow image strip, the baselines can be well approximated by straight line segments.

Based on these observations, the method proposes a constrained optimal curvilinear projection to estimate the baselines. This approach allows for the extraction of complete baselines with high accuracy for every pixel in the image, not just textual regions. It is designed to be segment-free and robust to various types of visual cues, including horizontal text lines, lines in tables, and boundaries of inserted photos and pages.

- manual_score: 1
- manual_notes: Partially correct and grounded in the two observations plus constrained curvilinear projection, but the high-level explanation is incomplete and adds extra details not clearly supported by these Top sources.

#### Question 8

**Question:** Which algorithm is used to solve the optimization problem?

**Retrieval backend:** chroma
**Retrieval time:** 0.34 s
**Generation time:** 11.498 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 41, "score": 0.7093, "vector_score": 0.5527, "lexical_score": 1.0, "snippet": "ataset can be downloaded from http://www.csse.uwa.\nedu.au/˜shafait/downloads.html\n3929\n[Extração completa Docling/OCR]\nand Ok, the weight on this edge, denoted by wij, is given\n<!-- formula-not-decoded -->\nwhere p is a predefined exponent in Eq.(4), Ak is the fixed interval in Eq.(7) for sampling k and\n<!-- formula-not-decoded -->\nAfter G' is constructed, the optimization of Eq.(4) turns out to be"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.6193, "vector_score": 0.4912, "lexical_score": 0.8571, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 33, "score": 0.5942, "vector_score": 0.5296, "lexical_score": 0.7143, "snippet": "ansform.\n## 2.2.2 Optimized strip projection\nWe can estimate the optimal projection lines across the central line L of a strip by solving the following constrained optimization problem, i.e.,\n<!-- formula-not-decoded -->\ngiven the constraints that two adjacent projection lines defined by Ok and Ok+1 do not intersect between the boundaries of the strip. The explicit expression of these constraints "}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 36, "score": 0.5701, "vector_score": 0.4925, "lexical_score": 0.7143, "snippet": "the strip, the line must fall in the red angular area determined by A, B and point (, ks). Thus, to satisfy the non-intersecting condition, Oks has to be limited within:\n<!-- formula-not-decoded -->\nIn the construction of G, every directed edge is also assigned a weight. For an edge connecting two vertices 0is-1\n[Página 5]\nand θj\nks\n, the weight on this edge, denoted by wij\ns , is given\nas:\nwij\ns "}]`

**Generated answer:**

The optimization problem is solved using Dijkstra's algorithm. This is mentioned in the context as follows:

"After G' is constructed, the optimization of Eq.(4) turns out to be finding an optimal path that passes through G and maximizes the total sum of the weights of edges on the path. By adding a virtual starting node and ending node to the left and right side of G respectively, the problem turns to be a classic longest path problem, which can be efficiently solved by the Dijkstra's algorithm [5]."

Therefore, Dijkstra's algorithm is used to solve the optimization problem.

- manual_score: 0
- manual_notes: Unsupported by the visible Top sources. The snippets explicitly mention a dynamic programming algorithm, while the answer asserts Dijkstra and quotes text not visible in the provided evidence.

#### Question 9

**Question:** What are the main experimental results described in the paper?

**Retrieval backend:** chroma
**Retrieval time:** 0.317 s
**Generation time:** 23.398 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 62, "score": 0.511, "vector_score": 0.5169, "lexical_score": 0.5, "snippet": ") the coarse estimation of baselines by Tian and Narasimhan’s method, (c) the reﬁnement results of Tian and Narasimhan’s\nmethod, (d) the separating seams produced by Nikolaos and Sabine’s method, (e) the estimated baselines by Nikolaos and Sabine’s method,\n(f) the extracted baselines by our method.\ntions on improving this paper. This work was supported in\npart by the projects of the National Natur"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 44, "score": 0.4994, "vector_score": 0.499, "lexical_score": 0.5, "snippet": "e.\n## 3. Experimental Results\nTo test the performance of the proposed method, we carried out a series of experiments on a great number of curved document images. These testing images include samples of scanned book pages and pages captured from books, magazines and paper sheets by a hand-held camera. In the experiments, we empirically set the exponent p = 3 and 1 = 1 in Eq.(4) and o = 1 for the sm"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 43, "score": 0.485, "vector_score": 0.4769, "lexical_score": 0.5, "snippet": "abeled as \"150\" o\nFigure 5. Results of the estimated baselines on the strip in Figure 3(a). (a) the solved optimal path (red curve) on R, (b) the estimated baselines on the strip, (c) the projection profiles of strip along a fixed direction, (d) the projection profiles of strip along the\n<!-- image -->\n## 2.3. Baselines Connection Between Strips\nAfter the baselines on each strip are estimated, we "}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 38, "score": 0.4816, "vector_score": 0.4717, "lexical_score": 0.5, "snippet": "lines on\nthe whole document page. The connection of baselines be-\ntween neighboring strips is much straightforward. In this\nprocess, a basic step is to determine the ending point of a\nbaseline giving its starting point. This can be quickly com-\nputed by using the equations of baselines in Eq.(3). Recall\nthat two neighboring strips overlap each other. We thereby\nsimply set the starting and ending p"}]`

**Generated answer:**

The main experimental results described in the paper include:

1. **Baseline Extraction on Curved Document Images**: The authors tested their method on a large number of curved document images, including samples from scanned book pages and pages captured from books, magazines, and paper sheets using a hand-held camera.

2. **Parameter Settings**: For the experiments, they empirically set the parameters as follows:
   - Exponent \( p = 3 \) and \( \lambda = 1 \) in Eq.(4)
   - Standard deviation \( \sigma = 1 \) for the smoothness term in Eq.(5)
   - 30 samples of \( k \) and discetized \( \theta \) uniformly in \([45^\circ, 135^\circ]\) by a fixed angle step of \( 1^\circ \)

3. **Edge Map Computation**: The Canny operator was used to compute the edge map of each input image. A 3 × 3 closing operation followed by morphological removing and dilation operations were applied to the edge map to remove some dotted noises.

4. **Strips Division**: The edge map was divided into 2030 strips of the same size according to the image width, with every two neighboring strips sharing 50% overlapping.

5. **Baseline Estimation and Connection**: After estimating the baselines on each strip, the authors connected the baselines between neighboring strips by setting the starting and ending points of all baselines at the center lines of the overlapping areas. Each extracted baseline was further smoothed by a cubic spline.

6. **Comparison with Other Methods**: The paper also includes comparisons of their method with Koo and Cho's method, as shown in Figure 9.

These results demonstrate the effectiveness of the proposed method in extracting baselines from curved document images.

- manual_score: 1
- manual_notes: Partially grounded: it correctly notes broad experiments on many curved document images and comparison with another method, but much of the answer is experimental setup detail not supported by the visible snippets and not really the main results.

#### Question 10

**Question:** According to the paper, what kinds of robustness does the method demonstrate?

**Retrieval backend:** chroma
**Retrieval time:** 0.334 s
**Generation time:** 13.461 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 49, "score": 0.4912, "vector_score": 0.5763, "lexical_score": 0.3333, "snippet": "ptured document image. This is because that the camera is hard to focus accurately on the document page when it gets distorted. To test the robustness of our method to such kind of blurring, we make a sequence of blurring images by filtering a clear document image with different Gaussian kernels. Figure 8 shows the results of baseline extraction on these images. As can be seen from the results, ou"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 44, "score": 0.4804, "vector_score": 0.4998, "lexical_score": 0.4444, "snippet": "e.\n## 3. Experimental Results\nTo test the performance of the proposed method, we carried out a series of experiments on a great number of curved document images. These testing images include samples of scanned book pages and pages captured from books, magazines and paper sheets by a hand-held camera. In the experiments, we empirically set the exponent p = 3 and 1 = 1 in Eq.(4) and o = 1 for the sm"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 47, "score": 0.4631, "vector_score": 0.533, "lexical_score": 0.3333, "snippet": ", respectively. The left-most three images come\nfrom English documents and the right-most four images come from Chinese documents. The last image is a scanned book page.\nOut-of-focus blurring commonly happens to a camera-\ncaptured document image. This is because that the camera\nis hard to focus accurately on the document page when it\ngets distorted. To test the robustness of our method to such\nkin"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 63, "score": 0.4544, "vector_score": 0.5196, "lexical_score": 0.3333, "snippet": "t images.<end_of_utteranc\nFigure 9. Comparisons of our method with Koo and Cho's method [9]. (a) the curved document images, (b) edge maps used by Koo and Cho's method, (c) text-lines extraction and fitting by Koo and Cho's method, (d) edge maps used by our method, (e) baseline extraction by our method (totally 25 strips used), (f) the close-up image patches of results by Koo and Cho's method (top"}]`

**Generated answer:**

According to the paper, the method demonstrates robustness to:

1. Image blurring: The method yields stable results for images with different levels of blurring, as tested by filtering clear document images with different Gaussian kernels. This robustness also extends to image down-sampling, which results in similar blurring.

2. Changes in image resolutions: Since image down-sampling leads to similar blurring effects, the method is not sensitive to changes in image resolutions.

3. Touching neighboring characters and text lines: The method is insensitive to these cases, which are common in curved document images captured by hand-held cameras.

These robustness properties are beneficial for the process of image noise removal, as they allow for the use of larger smoothing kernels without significantly losing accuracy in baseline extraction.

- manual_score: 1
- manual_notes: Partially correct. The snippets support robustness to out-of-focus blurring, but the claims about resolution changes, touching characters/text lines, and broader implications go beyond the shown evidence.

#### Question 11

**Question:** What is the central topic of the document?

**Retrieval backend:** chroma
**Retrieval time:** 0.59 s
**Generation time:** 10.208 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 64, "score": 0.4582, "vector_score": 0.4896, "lexical_score": 0.4, "snippet": "roving this paper. This work was supported in part by the projects of the National Natural Science Founda- tion of China (Grant No. 61370039, 61272331, 91338202).\n[Página 9]\nReferences\n[1] S. Avidan and A. Shamir. Seam carving for content-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dinstein. Line seg-\nmentation for degrad"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 7, "score": 0.4517, "vector_score": 0.4796, "lexical_score": 0.4, "snippet": "to efficiently solve the problem. The proposed method can extract the complete baselines through each pixel of document images in a high accuracy. It is also scripts insensitive and highly robust to image noises, non-textual objects, image resolutions and image quality degradation like blurring and non-uniform illumination. Extensive experiments on a number of captured document images demonstrate "}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 2, "score": 0.4489, "vector_score": 0.4752, "lexical_score": 0.4, "snippet": "sic ob-\nservations that the baselines of documents do not intersect\nwith each other and that within a narrow strip, the base-\nlines can be well approximated by linear segments. Based\nupon these observations, we propose a curvilinear projec-\ntion based method and model the estimation of curved base-\nlines as a constrained sequential optimization problem. A\ndynamic programming algorithm is then deve"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 1, "score": 0.4475, "vector_score": 0.4731, "lexical_score": 0.4, "snippet": "[Página 1]\nExtraction of Virtual Baselines from Distorted Document Images\nUsing Curvilinear Projection\nGaofeng MENG∗†, Zuming HUANG†, Y onghong SONG‡,\nShiming XIANG† and Chunhong PAN†\n† National Laboratory of Pattern Recognition, Institute of Automation\nChinese Academy of Sciences, Beijing P .R.China, 100190\nEmail: {gfmeng, smxiang, chpan }@nlpr.ia.ac.cn, huangzuming2014@ia.ac.cn\n‡ Institute of Ar"}]`

**Generated answer:**

The central topic of the document is the accurate extraction of virtual baselines from distorted document images using a curvilinear projection method. The document describes a method that models the estimation of curved baselines as a constrained sequential optimization problem and uses a dynamic programming algorithm to efficiently solve this problem. The method is robust to various image qualities and non-textual objects, and can extract complete baselines accurately from each pixel of document images.

- manual_score: 2
- manual_notes: Correct and well supported by the title and method snippets: the paper is about extracting virtual baselines from distorted document images using curvilinear projection.

#### Question 12

**Question:** What are the 3 most important sections or takeaways?

**Retrieval backend:** chroma
**Retrieval time:** 0.194 s
**Generation time:** 19.016 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 11, "score": 0.4309, "vector_score": 0.4321, "lexical_score": 0.4286, "snippet": "11] treat text\nlines extraction as an image segmentation problem. Inspired\nby the great success of seam carving in image resizing [1],\nRaid et al. [23] propose to use seam carving to automati-\ncally segment text lines from binary or gray-scale images of\nhandwritten documents. However, their method often pro-\nduces seams that cut through words and line components.\nNikolaos and Sabine [19] later imp"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 17, "score": 0.4205, "vector_score": 0.4162, "lexical_score": 0.4286, "snippet": "problem. Inspired by the great success of seam carving in image resizing [1], Raid et al.[23] propose to use seam carving to automatically segment text lines from binary or gray-scale images of' handwritten documents. However, their method often produces seams that cut through words and line components. Nikolaos and Sabine [19] later improve the method by incorporating some constraints into the op"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 8, "score": 0.3905, "vector_score": 0.447, "lexical_score": 0.2857, "snippet": "stimated reliably in a high\naccuracy. However, this is often a quite challenging task,\ndue to image distortion, various types of non-textual ob-\njects and the image quality degradation introduced during\nthe imaging process such as image blurring, low resolutions\nand non-uniform illumination.\nTypically, the baselines of a document image can be es-\ntimated by ﬁtting the horizontal text lines. To thi"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 14, "score": 0.3857, "vector_score": 0.4395, "lexical_score": 0.2857, "snippet": "owever, this is often a quite challenging task, due to image distortion, various types of non-textual objects and the image quality degradation introduced during the imaging process such as image blurring, low resolutions and non-uniform illumination.\nTypically, the baselines of a document image can be estimated by fitting the horizontal text lines. To this end, horizontal text lines in document i"}]`

**Generated answer:**

Based on the provided context, here are three important sections or takeaways:

1. **Text Line Segmentation Methods**:
   - **Segmentation Based Methods**: These methods treat text line extraction as an image segmentation problem, inspired by seam carving techniques. They are more general-purpose and require less knowledge about document layouts and scripts. However, they are sensitive to image noises, changes in image resolution, and overlapping text lines.
   - **Projection Based Methods**: These methods compute projection profiles over the entire image or vertical strips to locate text lines. They are effective but generally cannot reliably estimate baselines in high accuracy due to image distortions and quality degradation.

2. **Challenges in Text Line Extraction**:
   - The process of extracting text lines from document images is challenging due to image distortions, non-textual objects, and image quality issues like blurring, low resolution, and non-uniform illumination.
   - Early methods, such as tracing based methods, are often scripts sensitive and unstable, especially for characters with multiple components.

3. **Classification of Text Line Extraction Methods**:
   - Text line extraction methods can be classified into four major categories: tracing based methods, clustering based methods, segmentation based methods, and projection based methods.
   - Tracing based methods involve picking up a connected component as a seed and performing seed growing by linking it to nearest neighbors, which can be unstable and scripts sensitive.

- manual_score: 1
- manual_notes: Weakly grounded. It pulls plausible background points from the intro snippets, but these are not clearly the document’s three most important takeaways and include unsupported classification detail.

#### Question 13

**Question:** Does the document contain tables? What do they show?

**Retrieval backend:** chroma
**Retrieval time:** 0.281 s
**Generation time:** 11.079 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 40, "score": 0.5216, "vector_score": 0.5333, "lexical_score": 0.5, "snippet": "s inserted formulas\nand photos. This is mainly because the proposed method\ncan well exploit the available visual cues, such as text lines,\nhorizontal lines in tables and page boundaries, to infer the\nbaselines in the blank areas and non-textual regions.\nWe also give more results of our method on gray-scale\ndocument images in Figure 7. These images include pages\ncaptured by a hand-held camera or sc"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 7, "score": 0.4826, "vector_score": 0.5406, "lexical_score": 0.375, "snippet": "to efficiently solve the problem. The proposed method can extract the complete baselines through each pixel of document images in a high accuracy. It is also scripts insensitive and highly robust to image noises, non-textual objects, image resolutions and image quality degradation like blurring and non-uniform illumination. Extensive experiments on a number of captured document images demonstrate "}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 1, "score": 0.4817, "vector_score": 0.5391, "lexical_score": 0.375, "snippet": "[Página 1]\nExtraction of Virtual Baselines from Distorted Document Images\nUsing Curvilinear Projection\nGaofeng MENG∗†, Zuming HUANG†, Y onghong SONG‡,\nShiming XIANG† and Chunhong PAN†\n† National Laboratory of Pattern Recognition, Institute of Automation\nChinese Academy of Sciences, Beijing P .R.China, 100190\nEmail: {gfmeng, smxiang, chpan }@nlpr.ia.ac.cn, huangzuming2014@ia.ac.cn\n‡ Institute of Ar"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 64, "score": 0.4319, "vector_score": 0.5299, "lexical_score": 0.25, "snippet": "roving this paper. This work was supported in part by the projects of the National Natural Science Founda- tion of China (Grant No. 61370039, 61272331, 91338202).\n[Página 9]\nReferences\n[1] S. Avidan and A. Shamir. Seam carving for content-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dinstein. Line seg-\nmentation for degrad"}]`

**Generated answer:**

Based on the provided context, the document mentions the exploitation of "horizontal lines in tables" as one of the visual cues used to infer baselines in blank areas and non-textual regions. However, it does not explicitly state whether the document images themselves contain tables or what they show. The focus is more on the method's ability to extract baselines using various visual cues, including text lines and horizontal lines in tables, from document images that may contain large areas of non-textual objects.

- manual_score: 2
- manual_notes: Appropriately conservative. The snippets only mention horizontal lines in tables as cues; they do not clearly show whether the paper itself contains tables or what any table shows.

#### Question 14

**Question:** Does the document contain figures or diagrams? What do they show?

**Retrieval backend:** chroma
**Retrieval time:** 0.366 s
**Generation time:** 22.832 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 40, "score": 0.4685, "vector_score": 0.5413, "lexical_score": 0.3333, "snippet": "s inserted formulas\nand photos. This is mainly because the proposed method\ncan well exploit the available visual cues, such as text lines,\nhorizontal lines in tables and page boundaries, to infer the\nbaselines in the blank areas and non-textual regions.\nWe also give more results of our method on gray-scale\ndocument images in Figure 7. These images include pages\ncaptured by a hand-held camera or sc"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 63, "score": 0.4356, "vector_score": 0.5505, "lexical_score": 0.2222, "snippet": "t images.<end_of_utteranc\nFigure 9. Comparisons of our method with Koo and Cho's method [9]. (a) the curved document images, (b) edge maps used by Koo and Cho's method, (c) text-lines extraction and fitting by Koo and Cho's method, (d) edge maps used by our method, (e) baseline extraction by our method (totally 25 strips used), (f) the close-up image patches of results by Koo and Cho's method (top"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 44, "score": 0.43, "vector_score": 0.5419, "lexical_score": 0.2222, "snippet": "e.\n## 3. Experimental Results\nTo test the performance of the proposed method, we carried out a series of experiments on a great number of curved document images. These testing images include samples of scanned book pages and pages captured from books, magazines and paper sheets by a hand-held camera. In the experiments, we empirically set the exponent p = 3 and 1 = 1 in Eq.(4) and o = 1 for the sm"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 64, "score": 0.4283, "vector_score": 0.5393, "lexical_score": 0.2222, "snippet": "roving this paper. This work was supported in part by the projects of the National Natural Science Founda- tion of China (Grant No. 61370039, 61272331, 91338202).\n[Página 9]\nReferences\n[1] S. Avidan and A. Shamir. Seam carving for content-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dinstein. Line seg-\nmentation for degrad"}]`

**Generated answer:**

Yes, the document contains figures and diagrams. Based on the context provided:

1. **Figure 7**: This figure shows more results of the method on gray-scale document images. The images include pages from books, magazines, and paper sheets, some of which contain large areas of non-textual objects. The results demonstrate that the method works well on these gray-scale images, correctly extracting curved baselines in blank and non-textual object regions.

2. **Figure 9**: This figure compares the proposed method with Koo and Cho's method. It includes:
   - (a) Curved document images.
   - (b) Edge maps used by Koo and Cho's method.
   - (c) Text-line extraction and fitting by Koo and Cho's method.
   - (d) Edge maps used by the proposed method.
   - (e) Baseline extraction by the proposed method (using 25 strips).
   - (f) Close-up image patches of results by Koo and Cho's method (top) and the proposed method (bottom).

3. **Figure 10**: This figure compares the proposed method with Tian and Narasimhan's method and Nikolaos and Sabine's method. It includes:
   - (a) Curved images.
   - (b) Coarse estimation of baselines by Tian and Narasimhan's method.
   - (c) Refinement results of Tian and Narasimhan's method.
   - (d) Separating seams produced by Nikolaos and Sabine's method.
   - (e) Estimated baselines by Nikolaos and Sabine's method.
   - (f) Extracted baselines by the proposed method.

These figures provide visual comparisons and results of the proposed method against other methods, showing the performance on various types of document images.

- manual_score: 1
- manual_notes: Partially correct: the snippets support that the paper has figures and give evidence for Figure 7 and Figure 9, but the answer also adds Figure 10 details that are not present in these Top sources.

#### Question 15

**Question:** What is one important piece of information from the middle of the document?

**Retrieval backend:** chroma
**Retrieval time:** 0.324 s
**Generation time:** 8.896 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 47, "score": 0.4381, "vector_score": 0.4946, "lexical_score": 0.3333, "snippet": ", respectively. The left-most three images come\nfrom English documents and the right-most four images come from Chinese documents. The last image is a scanned book page.\nOut-of-focus blurring commonly happens to a camera-\ncaptured document image. This is because that the camera\nis hard to focus accurately on the document page when it\ngets distorted. To test the robustness of our method to such\nkin"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 1, "score": 0.4333, "vector_score": 0.4871, "lexical_score": 0.3333, "snippet": "[Página 1]\nExtraction of Virtual Baselines from Distorted Document Images\nUsing Curvilinear Projection\nGaofeng MENG∗†, Zuming HUANG†, Y onghong SONG‡,\nShiming XIANG† and Chunhong PAN†\n† National Laboratory of Pattern Recognition, Institute of Automation\nChinese Academy of Sciences, Beijing P .R.China, 100190\nEmail: {gfmeng, smxiang, chpan }@nlpr.ia.ac.cn, huangzuming2014@ia.ac.cn\n‡ Institute of Ar"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 48, "score": 0.4311, "vector_score": 0.4837, "lexical_score": 0.3333, "snippet": "e process of image noise removal, since we can\nchoose a larger kernel for image smoothing without signif-\n3930\n[Extração completa Docling/OCR]\nIn this image I can see the numbers and text.<end_of_utteranc\nFigure 6. Example results of baseline extraction from the curved document images in DFKI dataset. From top to bottom: the curved document images, the extracted virtual baselines, the projections "}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 64, "score": 0.4038, "vector_score": 0.5016, "lexical_score": 0.2222, "snippet": "roving this paper. This work was supported in part by the projects of the National Natural Science Founda- tion of China (Grant No. 61370039, 61272331, 91338202).\n[Página 9]\nReferences\n[1] S. Avidan and A. Shamir. Seam carving for content-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dinstein. Line seg-\nmentation for degrad"}]`

**Generated answer:**

One important piece of information from the middle of the document is that the proposed method is robust to image blurring, as demonstrated by testing it on images with varying levels of Gaussian blurring. This robustness also implies that the method is not sensitive to changes in image resolutions due to downsampling.

- manual_score: 1
- manual_notes: Partially grounded. The snippets support robustness to blur as a middle-document result, but the added claim about downsampling/resolution is not clearly visible in the provided evidence.

#### Question 16

**Question:** What is one limitation, note, or important observation mentioned near the end?

**Retrieval backend:** chroma
**Retrieval time:** 0.299 s
**Generation time:** 8.086 s
**Top sources:** `[{"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 64, "score": 0.3415, "vector_score": 0.4177, "lexical_score": 0.2, "snippet": "roving this paper. This work was supported in part by the projects of the National Natural Science Founda- tion of China (Grant No. 61370039, 61272331, 91338202).\n[Página 9]\nReferences\n[1] S. Avidan and A. Shamir. Seam carving for content-aware\nimage resizing. ACM Transactions on graphics (TOG) ,\n26(3):10, 2007.\n[2] I. Bar-Y osef, N. Hagbi, K. Kedem, and I. Dinstein. Line seg-\nmentation for degrad"}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 33, "score": 0.3033, "vector_score": 0.4128, "lexical_score": 0.1, "snippet": "ansform.\n## 2.2.2 Optimized strip projection\nWe can estimate the optimal projection lines across the central line L of a strip by solving the following constrained optimization problem, i.e.,\n<!-- formula-not-decoded -->\ngiven the constraints that two adjacent projection lines defined by Ok and Ok+1 do not intersect between the boundaries of the strip. The explicit expression of these constraints "}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 9, "score": 0.3026, "vector_score": 0.4117, "lexical_score": 0.1, "snippet": "erform\nseed growing by linking the seed to its nearest neighbors.\nTracing on CCs is generally scripts sensitive and very unsta-\nble. For characters with multiple components, e.g., Chinese\ncharacters, tracing on them often fails to yield the correct\ntext lines.\nLater improvements directly implement tracing on the\ngray-scale images. Tian and Narasimhan [25] observe that\npatches extracted from a set "}, {"source": "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf", "document_id": "1f4bbc821e9463e0b553b149691705cf845a282397e56df8249502258c3590fd", "file_type": "pdf", "chunk_id": 15, "score": 0.3024, "vector_score": 0.4114, "lexical_score": 0.1, "snippet": "s nearest neighbors. Tracing on CCs is generally scripts sensitive and very unstable. For characters with multiple components, e.g., Chinese characters, tracing on them often fails to yield the correct text lines.\nLater improvements directly implement tracing on the gray-scale images. Tian and Narasimhan [25] observe that patches extracted from a set of points along a text line are similar to each"}]`

**Generated answer:**

One limitation mentioned near the end is that tracing methods based on tracing characters or connected components (CCs) are vulnerable to page layouts, changes in font sizes, and non-textual image contents, leading to inaccurate tracing of curved text lines.

- manual_score: 0
- manual_notes: Unsupported and off-target. The visible Top sources near the end are references/other unrelated snippets, not a near-end limitation about tracing methods; this appears hallucinated from wrong retrieval.
