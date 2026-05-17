# PDF Extraction Benchmark Review

Generated at: 2026-03-15 01:12:42
Provider: ollama · Model: qwen2.5:7b · Prompt profile: neutral

## How to use this review file

For each question, fill in:
- `manual_score`: 0, 1, or 2
- `manual_notes`: comments about answer quality, retrieval quality, and noise

---

Review packet: 06
Document: kaur-2016-ijca-911367.pdf
Mode: complete — Completo por página · cobertura máxima com Docling/OCR
Questions in this packet: 16

### Mode: complete — Completo por página · cobertura máxima com Docling/OCR

- Extraction time: 56.617 s
- Indexing time: 4.817 s
- Final characters: 53131
- Chunks: 53
- Docling mode: page_complete
- Suspicious pages: [1]
- Pages processed with Docling: [1, 2, 3, 4]

#### Question 1

**Question:** What main problem does the paper try to solve?

**Retrieval backend:** chroma
**Retrieval time:** 0.136 s
**Generation time:** 10.496 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 40, "score": 0.4391, "vector_score": 0.4736, "lexical_score": 0.375, "snippet": "racters and numerals. The two methods were proposed and both works on the blocks of an images. The information from each block was concatenated to form a single feature vector of dimensionality 2000. The method was tested on two different dataset each having 7000 and 2000 binary images. The recognition rate of Gurmukhi characters and numerals were found out to be 97.38% and 99.65%. The work was al"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 6, "score": 0.4308, "vector_score": 0.4609, "lexical_score": 0.375, "snippet": "e feature vector of dimensionality 2000. The\nmethod was tested on two different dataset each having 7000\nand 2000 binary images. The recognition rate of Gurmukhi\ncharacters and numerals were found  out to be 97.38% and\n99.65%. The work was also extended to find out collective\naccuracy of methodology for both characters and numerals.\nThe main problem in Gurmukhi script recognition in case of\nmachin"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.4053, "vector_score": 0.489, "lexical_score": 0.25, "snippet": "and Offline Character recognition and Offline character recognition further divided into two parts: - machine printed and handwritten character recognition [2]. Handwritten character recognition has many problems like different writing styles, variation in pen-tip, skewness in writing etc. OCR plays an important role in improvement of interface between computer and man [3]. Character recognition i"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 38, "score": 0.398, "vector_score": 0.4777, "lexical_score": 0.25, "snippet": "valuable Punjabi literature which will further help in its conservation. The importance of OCR in transforming the documents into machine readable form, have led to great advancement in the field which are limited to the other languages like English, Arabic and Chinese languages\nIn Punjabi, most of the work is focused on online or offline handwritten character recognition and very little work is d"}]`

**Generated answer:**

The paper tries to solve the main problem of recognizing Gurmukhi script in machine-printed characters. Specifically, it addresses issues like the connectivity of characters on headlines, the presence of many similar characters, and the challenge of two or more characters in a word having intersecting minimum bounding rectangles.

- manual_score: 2
- manual_notes: Correct and grounded in snippets about printed Gurmukhi recognition; challenges like connected headlines/similar characters are supported, though one snippet is truncated.

#### Question 2

**Question:** What are the main contributions of the work?

**Retrieval backend:** chroma
**Retrieval time:** 0.312 s
**Generation time:** 18.982 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 38, "score": 0.4682, "vector_score": 0.4511, "lexical_score": 0.5, "snippet": "valuable Punjabi literature which will further help in its conservation. The importance of OCR in transforming the documents into machine readable form, have led to great advancement in the field which are limited to the other languages like English, Arabic and Chinese languages\nIn Punjabi, most of the work is focused on online or offline handwritten character recognition and very little work is d"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 27, "score": 0.3926, "vector_score": 0.4246, "lexical_score": 0.3333, "snippet": "performance is analyzed using different combinations of\nSVM type and its kernels on 10 -fold cross validation\nprocedure. The highest accuracy obtained on SVM is 97.87%\nwith the combination of nu -SVC type and RBF kernel. In\nfuture, this work can be extended on handwritten Gurumukhi\ncharacter recognition due to its high performance.\n6. REFERENCES\n[1] A. Jindal, R. Dhir, and R. Rani, “Diagonal Featu"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 42, "score": 0.3412, "vector_score": 0.4351, "lexical_score": 0.1667, "snippet": "e dataset nto the different propositions which were further used as the raining and testing. Two features were extracted from each images and tested on the two classifiers SVM and k-NN. inear and polynomial kernel functions were applied in case f SVM and k-NN were tested with 1, 3, 5 and 7 as different values for k [9].\ncollected The dataset consist of 7000 images of same size were from 20 writers"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 53, "score": 0.2909, "vector_score": 0.4475, "lexical_score": 0.0, "snippet": "P), 2011.\n9. 91 M. K. Mahto, K. Bhatia, and R. K. Sharma, \"Combine lorizontal and Vertical Prolection Feature Extractic Technique for Gurmukhi Handwritten Character Recognition,\" in International Conference on Advances in Computer Engineering and Applications (ICACEA), 2015.\n- [10] S. Singh, A. Aggarwal, and R. Dhir, \"Use of Gabor Filters for Recognition of Handwritten Gurmukhi Character,\" Int. J."}]`

**Generated answer:**

The main contributions of the work, as described in the context, include:

1. **Proposed Algorithm for Gurmukhi Printed Character Recognition**: The paper proposes an algorithm for recognizing Gurmukhi printed characters using a large set of different fonts, which is a significant advancement given the limited work done in this area.

2. **Feature Extraction and Classification**: The study involves extracting two features from each image and testing them on two classifiers (SVM and k-NN). It also tested linear and polynomial kernel functions with SVM and different values for k with k-NN.

3. **High Accuracy**: The highest accuracy obtained using SVM was 97.87% with the combination of nu-SVC type and RBF kernel. This high performance is noted as a significant contribution.

4. **Use of Gabor Filters**: The methodology used Gabor-based features for training SVM, achieving 94.29% accuracy in Gurmukhi script classification with Gabor-based features of dimensionality 200.

5. **Cross-Validation Methodology**: The study employed a fivefold cross-validation method to evaluate and validate the proposed methodology, ensuring robustness and reliability of the results.

These contributions highlight the advancements in Gurmukhi character recognition, particularly in printed characters, and the effectiveness of the proposed techniques.

- manual_score: 1
- manual_notes: Partially grounded: the proposed printed-character method and strong SVM result fit the snippets, but Gabor features, fivefold CV, and several listed contributions are unsupported/noisy.

#### Question 3

**Question:** What does Figure 1 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.341 s
**Generation time:** 7.639 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 19, "score": 0.3641, "vector_score": 0.4256, "lexical_score": 0.25, "snippet": "ions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x and y coordinates\nThe final fea"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 22, "score": 0.361, "vector_score": 0.4207, "lexical_score": 0.25, "snippet": "which first includes feature extraction with respect to x-coordinate while second step extract feature with respect to y- coordinate. In the first step, for given input binary image, the first order moment (center of mass) is calculated for the x-coordinate and image is divided into two sub-images by x-coordinate. Then process is repeated recursively for newly generated subimages by transposing th"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 23, "score": 0.3571, "vector_score": 0.4148, "lexical_score": 0.25, "snippet": "f original and transposed image. The length of final vector will be 2*(2^d-1). Figure 4 shows the divisions of input image at different depth levels of x-coordinate and y-coordinates.\n## 3.4 Classification\nSupport Vector Machine (SVM) [13] is a supervised learning technique used for classification or regression. SVM was initially designed for binary classification, but now extended for solving mul"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 47, "score": 0.3565, "vector_score": 0.4139, "lexical_score": 0.25, "snippet": "4 Divisions of s at different depth levels along x and y coordinates\n<!-- image -->\nThe final feature vector is the concatenation of both vectors of original and transposed image. The length of final vector will be 2*(2^d-1). Figure 4 shows the divisions of input image at different depth levels of x-coordinate and y-coordinates.\n## 3.4 Classification\nSupport Vector Machine (SVM) [13] is a supervis"}]`

**Generated answer:**

The context provided does not contain any information about a Figure 1. The figures mentioned are Figure 4, which shows the divisions of the input image at different depth levels along x and y coordinates. Please provide more details or check the figure number you are referring to.

- manual_score: 1
- manual_notes: Does not answer Figure 1, but it avoids hallucinating and correctly notes retrieval mismatch; the shown sources only discuss Figure 4.

#### Question 4

**Question:** What does Figure 3 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.228 s
**Generation time:** 6.44 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 19, "score": 0.3488, "vector_score": 0.402, "lexical_score": 0.25, "snippet": "ions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x and y coordinates\nThe final fea"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 47, "score": 0.3444, "vector_score": 0.3953, "lexical_score": 0.25, "snippet": "4 Divisions of s at different depth levels along x and y coordinates\n<!-- image -->\nThe final feature vector is the concatenation of both vectors of original and transposed image. The length of final vector will be 2*(2^d-1). Figure 4 shows the divisions of input image at different depth levels of x-coordinate and y-coordinates.\n## 3.4 Classification\nSupport Vector Machine (SVM) [13] is a supervis"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 23, "score": 0.3439, "vector_score": 0.3944, "lexical_score": 0.25, "snippet": "f original and transposed image. The length of final vector will be 2*(2^d-1). Figure 4 shows the divisions of input image at different depth levels of x-coordinate and y-coordinates.\n## 3.4 Classification\nSupport Vector Machine (SVM) [13] is a supervised learning technique used for classification or regression. SVM was initially designed for binary classification, but now extended for solving mul"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 43, "score": 0.2733, "vector_score": 0.4204, "lexical_score": 0.0, "snippet": "tures and classifiers were tested for the recognition of Gurmukhi characters from documents. In first. 128 features comprised of distance profiles. Second feature set was different histogram projection of size 190 and in last zonal density and background directional distribution forming 144 features. These were applied on three classifiers names SVM, PNN and k-NN. The SVM was tested with radial ba"}]`

**Generated answer:**

The context provided does not contain any information about Figure 3. The descriptions and figures mentioned are related to Figure 4, which shows the divisions of the input image at different depth levels of x-coordinate and y-coordinates. Without the actual content of Figure 3, I cannot provide what it shows.

- manual_score: 1
- manual_notes: Again mostly flags missing evidence. Conservative and grounded, but incomplete because the retrieved snippets are about Figure 4, not Figure 3.

#### Question 5

**Question:** What does Figure 4 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.199 s
**Generation time:** 7.78 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 47, "score": 0.3596, "vector_score": 0.4186, "lexical_score": 0.25, "snippet": "4 Divisions of s at different depth levels along x and y coordinates\n<!-- image -->\nThe final feature vector is the concatenation of both vectors of original and transposed image. The length of final vector will be 2*(2^d-1). Figure 4 shows the divisions of input image at different depth levels of x-coordinate and y-coordinates.\n## 3.4 Classification\nSupport Vector Machine (SVM) [13] is a supervis"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 19, "score": 0.3561, "vector_score": 0.4132, "lexical_score": 0.25, "snippet": "ions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x and y coordinates\nThe final fea"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 23, "score": 0.3477, "vector_score": 0.4003, "lexical_score": 0.25, "snippet": "f original and transposed image. The length of final vector will be 2*(2^d-1). Figure 4 shows the divisions of input image at different depth levels of x-coordinate and y-coordinates.\n## 3.4 Classification\nSupport Vector Machine (SVM) [13] is a supervised learning technique used for classification or regression. SVM was initially designed for binary classification, but now extended for solving mul"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 22, "score": 0.338, "vector_score": 0.3854, "lexical_score": 0.25, "snippet": "which first includes feature extraction with respect to x-coordinate while second step extract feature with respect to y- coordinate. In the first step, for given input binary image, the first order moment (center of mass) is calculated for the x-coordinate and image is divided into two sub-images by x-coordinate. Then process is repeated recursively for newly generated subimages by transposing th"}]`

**Generated answer:**

Figure 4 shows the divisions of the input image at different depth levels along the x-coordinate and y-coordinate. This figure helps in understanding how the image is recursively divided to extract features at various depths, with the final feature vector being the concatenation of features from both the original and transposed images.

- manual_score: 2
- manual_notes: Correct and directly supported: Figure 4 shows recursive divisions of the input image at different x/y depth levels; the extra explanation remains consistent.

#### Question 6

**Question:** Which method or combination achieved the best performance?

**Retrieval backend:** chroma
**Retrieval time:** 0.207 s
**Generation time:** 8.102 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 50, "score": 0.572, "vector_score": 0.4954, "lexical_score": 0.7143, "snippet": "sults using different type of SVM and its Kernels\n|   Sr. No. | SVM type   | Kernel     |   Accuracy (%age) |\n|-----------|------------|------------|-------------------|\n|         1 | nu-SVC     | RBF        |             97.87 |\n|         2 | nu-SVC     | Linear     |             96.85 |\n|         3 | nu-SVC     | Polynomial |             96.59 |\n|         4 | C-SVC      | RBF        |           "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 14, "score": 0.4749, "vector_score": 0.4998, "lexical_score": 0.4286, "snippet": "he 10 different people where each belongs to different age group. Three strategies were formed by dividing the whole dataset nto the different propositions which were further used as the raining and testing. Two features were extracted from each images and tested on the two classifiers SVM and k-NN. inear and polynomial kernel functions were applied in case f SVM and k-NN were tested with 1, 3, 5 "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.4731, "vector_score": 0.4971, "lexical_score": 0.4286, "snippet": "gnition take place. A hybrid classification is used classification is done by combining decision tree and nearest neighbor classifiers. The recognition rate and processing speed are found out to be 96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi characters by employing k-NN classifiers. First Skelton of each character is prepared in order to extra"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 42, "score": 0.4707, "vector_score": 0.4934, "lexical_score": 0.4286, "snippet": "e dataset nto the different propositions which were further used as the raining and testing. Two features were extracted from each images and tested on the two classifiers SVM and k-NN. inear and polynomial kernel functions were applied in case f SVM and k-NN were tested with 1, 3, 5 and 7 as different values for k [9].\ncollected The dataset consist of 7000 images of same size were from 20 writers"}]`

**Generated answer:**

Based on the information provided in the context, the best performance was achieved using the RBF kernel with the nu-SVC type of SVM. Specifically, the highest accuracy of 97.87% was obtained from the RBF kernel of the nu-SVC type of SVM.

- manual_score: 2
- manual_notes: Correct and well supported by the results table: nu-SVC with RBF kernel achieved the best accuracy (97.87%).

#### Question 7

**Question:** Which evaluation metric was used?

**Retrieval backend:** chroma
**Retrieval time:** 0.302 s
**Generation time:** 7.775 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 42, "score": 0.5654, "vector_score": 0.5467, "lexical_score": 0.6, "snippet": "e dataset nto the different propositions which were further used as the raining and testing. Two features were extracted from each images and tested on the two classifiers SVM and k-NN. inear and polynomial kernel functions were applied in case f SVM and k-NN were tested with 1, 3, 5 and 7 as different values for k [9].\ncollected The dataset consist of 7000 images of same size were from 20 writers"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 14, "score": 0.5555, "vector_score": 0.5315, "lexical_score": 0.6, "snippet": "he 10 different people where each belongs to different age group. Three strategies were formed by dividing the whole dataset nto the different propositions which were further used as the raining and testing. Two features were extracted from each images and tested on the two classifiers SVM and k-NN. inear and polynomial kernel functions were applied in case f SVM and k-NN were tested with 1, 3, 5 "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 8, "score": 0.4921, "vector_score": 0.5417, "lexical_score": 0.4, "snippet": "xtracted from each\nimages and tested on the two classifiers SVM and k -NN.\nLinear and polynomial kernel function s were applied in case\nof SVM and k -NN were tested with 1, 3, 5 and 7 as different\nvalues for k [9].\nThe dataset consist of 7000 images of same size were\ncollected from 20 writers of different age groups. In\npreprocessing stage, an image was converted to b inary by\nusing Otsu’s method."}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 41, "score": 0.4727, "vector_score": 0.5119, "lexical_score": 0.4, "snippet": "eighbor classifiers. The recognition rate and processing speed are found out to be 96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi characters by employing k-NN classifiers. First Skelton of each character is prepared in order to extract its feature information. Diagonal and transition features were calculated on the bitmap images of the characters"}]`

**Generated answer:**

The evaluation metric used in the study was accuracy, specifically 94.29% accuracy was reported for the Gurmukhi script classification using Gabor based features. Additionally, Munish et al. reported a recognition rate of 96.6%.

- manual_score: 1
- manual_notes: The metric 'accuracy' is correct, but the answer adds unsupported details from other studies/results; grounding is weak and noisy.

#### Question 8

**Question:** What does the main results table compare?

**Retrieval backend:** chroma
**Retrieval time:** 0.281 s
**Generation time:** 15.54 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 50, "score": 0.4839, "vector_score": 0.4368, "lexical_score": 0.5714, "snippet": "sults using different type of SVM and its Kernels\n|   Sr. No. | SVM type   | Kernel     |   Accuracy (%age) |\n|-----------|------------|------------|-------------------|\n|         1 | nu-SVC     | RBF        |             97.87 |\n|         2 | nu-SVC     | Linear     |             96.85 |\n|         3 | nu-SVC     | Polynomial |             96.59 |\n|         4 | C-SVC      | RBF        |           "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 19, "score": 0.463, "vector_score": 0.4816, "lexical_score": 0.4286, "snippet": "ions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x and y coordinates\nThe final fea"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 20, "score": 0.4437, "vector_score": 0.4519, "lexical_score": 0.4286, "snippet": "ucting a hyper plane  [15]. The main goal is to find an\noptimal hyper plane  which expects to generalize the\ncomparison to th e others. The optimal hyper plane  is one\nwhich maximizes a measure of the “margin” between such\nclasses. The unknown data sample is then classified by the\nSVM according to the decision boundaries defined by these\nhyper planes . Hyper planes  with maximum app ropriate\nmargi"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 23, "score": 0.399, "vector_score": 0.46, "lexical_score": 0.2857, "snippet": "f original and transposed image. The length of final vector will be 2*(2^d-1). Figure 4 shows the divisions of input image at different depth levels of x-coordinate and y-coordinates.\n## 3.4 Classification\nSupport Vector Machine (SVM) [13] is a supervised learning technique used for classification or regression. SVM was initially designed for binary classification, but now extended for solving mul"}]`

**Generated answer:**

The main results table compares the accuracy of different types of SVM (nu-SVC and C-SVC) with different kernels (RBF, Linear, Polynomial). Specifically, it shows that:

- nu-SVC with RBF kernel achieved the highest accuracy of 97.87%.
- nu-SVC with Linear kernel had an accuracy of 96.85%.
- nu-SVC with Polynomial kernel had an accuracy of 96.59%.
- C-SVC with RBF kernel had an accuracy of 97.72%.
- C-SVC with Linear kernel had an accuracy of 97.18%.
- C-SVC with Polynomial kernel had the same accuracy as the Polynomial kernel of nu-SVC, which was 96.59%.

The table indicates that RBF kernels generally provided the best results, followed by Linear kernels, and Polynomial kernels performed the worst among the tested kernels. Additionally, the results show that C-SVC type of SVM generally outperformed nu-SVC.

- manual_score: 1
- manual_notes: Main idea is right: the table compares SVM types, kernels, and accuracy. But several row values and conclusions go beyond the visible snippet.

#### Question 9

**Question:** What limitations or future work are mentioned?

**Retrieval backend:** chroma
**Retrieval time:** 0.387 s
**Generation time:** 12.211 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 38, "score": 0.3968, "vector_score": 0.431, "lexical_score": 0.3333, "snippet": "valuable Punjabi literature which will further help in its conservation. The importance of OCR in transforming the documents into machine readable form, have led to great advancement in the field which are limited to the other languages like English, Arabic and Chinese languages\nIn Punjabi, most of the work is focused on online or offline handwritten character recognition and very little work is d"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 4, "score": 0.395, "vector_score": 0.4282, "lexical_score": 0.3333, "snippet": "languages\nIn Punjabi, most of the work is focused on online or offline handwritten character recognition and very little work is done for printed character recognition. So, in this paper an algorithm has been proposed for the recognition of Gurmukhi printed character recognition using a large set of different types of fonts. Rest of the paper is structured as follows: work done so far in the field"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.3925, "vector_score": 0.4244, "lexical_score": 0.3333, "snippet": "and Offline Character recognition and Offline character recognition further divided into two parts: - machine printed and handwritten character recognition [2]. Handwritten character recognition has many problems like different writing styles, variation in pen-tip, skewness in writing etc. OCR plays an important role in improvement of interface between computer and man [3]. Character recognition i"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 40, "score": 0.3878, "vector_score": 0.4171, "lexical_score": 0.3333, "snippet": "racters and numerals. The two methods were proposed and both works on the blocks of an images. The information from each block was concatenated to form a single feature vector of dimensionality 2000. The method was tested on two different dataset each having 7000 and 2000 binary images. The recognition rate of Gurmukhi characters and numerals were found out to be 97.38% and 99.65%. The work was al"}]`

**Generated answer:**

Based on the provided context, there are no explicit mentions of specific limitations or future work in the given excerpts. The context primarily discusses the current state of research in Gurmukhi character recognition, focusing on the limited work done for printed character recognition compared to handwritten recognition. It also mentions some challenges in recognizing machine-printed Gurmukhi characters, such as the connectivity of characters, similar characters, and intersecting minimum bounding rectangles.

However, given the context, it can be inferred that future work might include:
- Expanding research on printed character recognition.
- Addressing the challenges mentioned for machine-printed characters.
- Improving the recognition rate and processing speed.

For precise information on limitations or future work, a more detailed section or conclusion of the paper would be needed.

- manual_score: 1
- manual_notes: Reasonable to note that the shown snippets do not explicitly give limitations/future work, but the inferred future-work bullets are unsupported additions.

#### Question 10

**Question:** At a high level, how does the method work based on both the text and the figures?

**Retrieval backend:** chroma
**Retrieval time:** 0.312 s
**Generation time:** 27.478 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 46, "score": 0.5043, "vector_score": 0.5514, "lexical_score": 0.4167, "snippet": "ized according the size of the input image Therefore the size of images does not affect the final feature set. The method is a two-step procedure in which first includes feature extraction with respect to x-coordinate while second step extract feature with respect to y- coordinate. In the first step, for given input binary image, the first order moment (center of mass) is calculated for the x-coor"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 14, "score": 0.4864, "vector_score": 0.5688, "lexical_score": 0.3333, "snippet": "he 10 different people where each belongs to different age group. Three strategies were formed by dividing the whole dataset nto the different propositions which were further used as the raining and testing. Two features were extracted from each images and tested on the two classifiers SVM and k-NN. inear and polynomial kernel functions were applied in case f SVM and k-NN were tested with 1, 3, 5 "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 42, "score": 0.4782, "vector_score": 0.5562, "lexical_score": 0.3333, "snippet": "e dataset nto the different propositions which were further used as the raining and testing. Two features were extracted from each images and tested on the two classifiers SVM and k-NN. inear and polynomial kernel functions were applied in case f SVM and k-NN were tested with 1, 3, 5 and 7 as different values for k [9].\ncollected The dataset consist of 7000 images of same size were from 20 writers"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 8, "score": 0.4722, "vector_score": 0.547, "lexical_score": 0.3333, "snippet": "xtracted from each\nimages and tested on the two classifiers SVM and k -NN.\nLinear and polynomial kernel function s were applied in case\nof SVM and k -NN were tested with 1, 3, 5 and 7 as different\nvalues for k [9].\nThe dataset consist of 7000 images of same size were\ncollected from 20 writers of different age groups. In\npreprocessing stage, an image was converted to b inary by\nusing Otsu’s method."}]`

**Generated answer:**

Based on the provided context, the method works as follows:

1. **Feature Extraction**:
   - The method uses a two-step procedure for feature extraction:
     - **First Step (X-coordinate)**: For a given input binary image, the first-order moment (center of mass) is calculated for the x-coordinate. The image is then divided into two sub-images by the x-coordinate. This process is repeated recursively, with the length of the feature vector given by \(2^d - 1\), where \(d\) is the recursive depth or divisions. Features are also calculated for the transposed image to balance the output vector.
     - **Second Step (Y-coordinate)**: A similar process is applied but this time with respect to the y-coordinate.

2. **Feature Vector Concatenation**:
   - The final feature vector is the concatenation of the vectors obtained from the original and transposed images.

3. **Image Preprocessing**:
   - The input image is first converted to a binary image using Otsu's method.
   - Median filtering and morphological operations are applied as part of the preprocessing stage.
   - Iterative segmentation is used to segment the characters.

4. **Feature Calculation**:
   - Gabor-based features (GABM and GABN) are used to train the SVM classifier.
   - Three different feature sets are tested:
     - 128 features based on distance profiles.
     - 190 features from different histogram projections.
     - 144 features from zonal density and background directional distribution.

5. **Classification**:
   - Two classifiers, SVM and k-NN, are used for classification.
   - SVM is tested with linear and polynomial kernel functions.
   - k-NN is tested with \(k\) values of 1, 3, 5, and 7.
   - Fivefold cross-validation is used to evaluate and validate the methodology.

6. **Accuracy**:
   - The methodology achieves 94.29% accuracy in Gurmukhi script classification using Gabor-based features of dimensionality 200.

This method effectively combines multiple feature extraction techniques and classifiers to achieve high accuracy in script recognition, particularly for Gurmukhi characters.

- manual_score: 1
- manual_notes: Contains the core two-step x/y recursive feature-extraction idea, but much of the rest (Gabor features, multiple classifiers, fivefold CV, etc.) is unsupported and mixed from other work.

#### Question 11

**Question:** What is the central topic of the document?

**Retrieval backend:** chroma
**Retrieval time:** 0.634 s
**Generation time:** 7.546 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 37, "score": 0.5141, "vector_score": 0.4679, "lexical_score": 0.6, "snippet": "Mohali, India\nFig. 2 Gurmukhi Numerals\n<!-- image -->\nOptical Character recognition (OCR) is a system which aims at transforming a document into computer readable form [1]. The document can be printed or handwritten form. OCR is further divided into subfields: - Online and Offline Character recognition and Offline character recognition further divided into two parts: - machine printed and handwrit"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 36, "score": 0.4201, "vector_score": 0.4309, "lexical_score": 0.4, "snippet": "ed by measuring accuracy using 10-fold cross validation procedure. The highest accuracy obtained on SVM is 97.87% with the combination of nu-SVC type and RBF kernel.\n## Keywords\nCharacter Recognition, Support Vector Machine, Printed Gurmukhi.\n## 1. INTRODUCTION\nMultiple languages are used among different people in India which mainly depends on their geographical locations. Gurmukhi is one of the l"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.4176, "vector_score": 0.4271, "lexical_score": 0.4, "snippet": "and Offline Character recognition and Offline character recognition further divided into two parts: - machine printed and handwritten character recognition [2]. Handwritten character recognition has many problems like different writing styles, variation in pen-tip, skewness in writing etc. OCR plays an important role in improvement of interface between computer and man [3]. Character recognition i"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 38, "score": 0.3511, "vector_score": 0.4324, "lexical_score": 0.2, "snippet": "valuable Punjabi literature which will further help in its conservation. The importance of OCR in transforming the documents into machine readable form, have led to great advancement in the field which are limited to the other languages like English, Arabic and Chinese languages\nIn Punjabi, most of the work is focused on online or offline handwritten character recognition and very little work is d"}]`

**Generated answer:**

The central topic of the document is the Optical Character Recognition (OCR) for the Gurmukhi script, particularly focusing on printed characters. The document discusses the importance of OCR for the Punjabi language and presents an algorithm for recognizing Gurmukhi printed characters using various fonts.

- manual_score: 2
- manual_notes: Correct and grounded in the keywords/introduction snippets: OCR for printed Gurmukhi / Punjabi character recognition.

#### Question 12

**Question:** What are the 3 most important sections or takeaways?

**Retrieval backend:** chroma
**Retrieval time:** 0.243 s
**Generation time:** 15.949 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.4738, "vector_score": 0.4212, "lexical_score": 0.5714, "snippet": "and Offline Character recognition and Offline character recognition further divided into two parts: - machine printed and handwritten character recognition [2]. Handwritten character recognition has many problems like different writing styles, variation in pen-tip, skewness in writing etc. OCR plays an important role in improvement of interface between computer and man [3]. Character recognition i"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 9, "score": 0.3777, "vector_score": 0.4273, "lexical_score": 0.2857, "snippet": "128 features comprised of distance profiles. Second feature\nset was different histogram projection of size 190 and in last\nzonal density and background directional distribution forming\n144 features. These were applied on three classifiers names\nSVM, PNN and k -NN. The SVM was tested with radial basis\nkernel function. The different parameters were varied of each\nclassifier to get best results. SVM "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 21, "score": 0.3725, "vector_score": 0.4193, "lexical_score": 0.2857, "snippet": "this approach, initially the\n[Extração completa Docling/OCR]\n## 3.2 Preprocessing\nImages of different types of font styles used in Punjabi language were acquired using a scanner. Firstly the characters are typed and their printout is taken. Then, each character of each font style is scanned one by one. The digitized images obtained after scanning are stored in a PNG format. Since digitized images "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 22, "score": 0.3702, "vector_score": 0.4157, "lexical_score": 0.2857, "snippet": "which first includes feature extraction with respect to x-coordinate while second step extract feature with respect to y- coordinate. In the first step, for given input binary image, the first order moment (center of mass) is calculated for the x-coordinate and image is divided into two sub-images by x-coordinate. Then process is repeated recursively for newly generated subimages by transposing th"}]`

**Generated answer:**

Based on the provided context, here are the 3 most important sections or takeaways:

1. **Character Recognition in Punjabi Language**: The paper focuses on the recognition of Punjabi language, specifically using the Gurmukhi script. It highlights that most work is done on handwritten character recognition, with very little focus on printed character recognition for Punjabi.

2. **Feature Extraction Methods**: The paper discusses various feature extraction methods. For printed characters, it mentions the hierarchical centroid method proposed by Armon, which involves recursive subdivisions of the input binary image to extract features based on x and y coordinates. This method ensures that the size of the images does not affect the final feature set.

3. **Classification Techniques**: The paper also describes the application of different classifiers (SVM, PNN, k-NN) and the use of a hybrid classification scheme involving a binary decision tree and nearest neighbor classifier. It notes that the SVM performed best with the second feature set, while PNN and k-NN performed best with the third feature set.

These sections provide a comprehensive overview of the research approach, methods, and results related to character recognition in the Punjabi language.

- manual_score: 1
- manual_notes: Some takeaways fit the snippets (OCR/Gurmukhi focus, preprocessing/feature extraction), but it mixes in unsupported claims from related work and extra classifiers.

#### Question 13

**Question:** Does the document contain tables? What do they show?

**Retrieval backend:** chroma
**Retrieval time:** 0.335 s
**Generation time:** 8.523 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 17, "score": 0.3863, "vector_score": 0.4597, "lexical_score": 0.25, "snippet": "nsists of 29 different font styles. Each character of every style is printed in three font sizes of 18, 24 and 30. There are total 35 characters in Punjabi and 10 numerals. So a dataset of 3915 images is\nIn this image, we can see some text and images.<end_of_utteranc\nFig. 3 Sample Font Styles of our Dataset\n<!-- image -->\n[Página 3]\nInternational Journal of Computer Applications (0975 – 8887)\nVolu"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 37, "score": 0.3771, "vector_score": 0.4455, "lexical_score": 0.25, "snippet": "Mohali, India\nFig. 2 Gurmukhi Numerals\n<!-- image -->\nOptical Character recognition (OCR) is a system which aims at transforming a document into computer readable form [1]. The document can be printed or handwritten form. OCR is further divided into subfields: - Online and Offline Character recognition and Offline character recognition further divided into two parts: - machine printed and handwrit"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 29, "score": 0.3441, "vector_score": 0.462, "lexical_score": 0.125, "snippet": "ers for Recognition of Han dwritten Gurmukhi\nCharacter,” Int. J. Adv. Res. Comput. Sci. Softw. Eng.,\nvol. 2, no. 5, pp. 234–240, 2012.\n[11] K. S. Siddharth, R. Dhir, R. Rani, M. Jangid, and K.\nSingh, “Comparative Recognition of Handwritten\nGurmukhi Numerals Using Different Feature S ets and\nClassifiers,” in Proceedings of International Conference\non Image Information Processing (ICIIP 2011), 2011."}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 19, "score": 0.341, "vector_score": 0.4573, "lexical_score": 0.125, "snippet": "ions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x and y coordinates\nThe final fea"}]`

**Generated answer:**

The provided context does not mention any tables. The information given is primarily textual, describing the dataset, preprocessing steps, feature extraction methods, and classification techniques. There are references to figures (Fig. 3, Fig. 4), but no tables are described or shown.

- manual_score: 1
- manual_notes: Conservative but incomplete. It reports no table evidence in the retrieved snippets, yet retrieval is clearly poor/noisy and the answer cannot confidently establish absence.

#### Question 14

**Question:** Does the document contain figures or diagrams? What do they show?

**Retrieval backend:** chroma
**Retrieval time:** 0.347 s
**Generation time:** 10.333 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 17, "score": 0.3703, "vector_score": 0.45, "lexical_score": 0.2222, "snippet": "nsists of 29 different font styles. Each character of every style is printed in three font sizes of 18, 24 and 30. There are total 35 characters in Punjabi and 10 numerals. So a dataset of 3915 images is\nIn this image, we can see some text and images.<end_of_utteranc\nFig. 3 Sample Font Styles of our Dataset\n<!-- image -->\n[Página 3]\nInternational Journal of Computer Applications (0975 – 8887)\nVolu"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 11, "score": 0.3504, "vector_score": 0.4793, "lexical_score": 0.1111, "snippet": "e proposed study. Size of images varies from\n20*21 pixels to 40*41 pixels with a bit depth of 1. The sample\nimages of font styles used in our dataset are shown in Figure\n3.\nStyle name Fonts sample\nAdami\nRangdar\nAdhiapak\nFig. 3 Sample Font Styles of our Dataset\n[Extração completa Docling/OCR]\nrecognition. Some of these studies are briefly reviewed as follows:\nThe zoning mechanism is used for the fe"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 42, "score": 0.3385, "vector_score": 0.461, "lexical_score": 0.1111, "snippet": "e dataset nto the different propositions which were further used as the raining and testing. Two features were extracted from each images and tested on the two classifiers SVM and k-NN. inear and polynomial kernel functions were applied in case f SVM and k-NN were tested with 1, 3, 5 and 7 as different values for k [9].\ncollected The dataset consist of 7000 images of same size were from 20 writers"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 39, "score": 0.3341, "vector_score": 0.4541, "lexical_score": 0.1111, "snippet": "ast 15 years, many researchers have tried to improve the OCR system for Gurmukhi language. Majority of the research is devoted to online and offline handwritten character/script\nrecognition. Some of these studies are briefly reviewed as follows:\nThe zoning mechanism is used for the feature extraction which is used to train support vector machine (SVM). This paper present a technique for the recogn"}]`

**Generated answer:**

Yes, the document contains figures or diagrams. Specifically, it mentions:

1. Figure 3 titled "Sample Font Styles of our Dataset" which shows examples of different font styles used in the dataset. This figure illustrates the variety of font styles and characters included, such as Adami, Rangdar, and Adhiapak.

These figures are useful for understanding the diversity of the dataset used in the study, which includes 29 different font styles, each with characters in three font sizes (18, 24, and 30), and a total of 3915 images (35 characters + 10 numerals).

- manual_score: 1
- manual_notes: Grounded for Figure 3/sample font styles, but incomplete because it only covers one visible figure and overextends with extra dataset detail.

#### Question 15

**Question:** What is one important piece of information from the middle of the document?

**Retrieval backend:** chroma
**Retrieval time:** 0.217 s
**Generation time:** 8.181 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 37, "score": 0.4606, "vector_score": 0.4693, "lexical_score": 0.4444, "snippet": "Mohali, India\nFig. 2 Gurmukhi Numerals\n<!-- image -->\nOptical Character recognition (OCR) is a system which aims at transforming a document into computer readable form [1]. The document can be printed or handwritten form. OCR is further divided into subfields: - Online and Offline Character recognition and Offline character recognition further divided into two parts: - machine printed and handwrit"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 2, "score": 0.4519, "vector_score": 0.456, "lexical_score": 0.4444, "snippet": "languages are used among different people in India which mainly depends on their geographical locations. Gurmukhi is one of the languages which is mostly used in northern region of India. This script was devised by first Sikh Guru, Sri Guru Nanak Dev ji in 16th century and popularized by second Sikh Guru, Sri Guru Angad Dev ji. Gurmukhi word is derived from two Sanskrit words Guru and Mukha which "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 36, "score": 0.4493, "vector_score": 0.452, "lexical_score": 0.4444, "snippet": "ed by measuring accuracy using 10-fold cross validation procedure. The highest accuracy obtained on SVM is 97.87% with the combination of nu-SVC type and RBF kernel.\n## Keywords\nCharacter Recognition, Support Vector Machine, Printed Gurmukhi.\n## 1. INTRODUCTION\nMultiple languages are used among different people in India which mainly depends on their geographical locations. Gurmukhi is one of the l"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 29, "score": 0.4119, "vector_score": 0.4543, "lexical_score": 0.3333, "snippet": "ers for Recognition of Han dwritten Gurmukhi\nCharacter,” Int. J. Adv. Res. Comput. Sci. Softw. Eng.,\nvol. 2, no. 5, pp. 234–240, 2012.\n[11] K. S. Siddharth, R. Dhir, R. Rani, M. Jangid, and K.\nSingh, “Comparative Recognition of Handwritten\nGurmukhi Numerals Using Different Feature S ets and\nClassifiers,” in Proceedings of International Conference\non Image Information Processing (ICIIP 2011), 2011."}]`

**Generated answer:**

One important piece of information from the middle of the document is that Optical Character Recognition (OCR) plays an important role in improving the interface between computers and humans. Specifically, the document states: "OCR plays an important role in improvement of interface between computer and man."

- manual_score: 1
- manual_notes: Supported by the snippets, but generic and not clearly from the document's middle; retrieval appears off-target.

#### Question 16

**Question:** What is one limitation, note, or important observation mentioned near the end?

**Retrieval backend:** chroma
**Retrieval time:** 0.251 s
**Generation time:** 7.709 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.3656, "vector_score": 0.4009, "lexical_score": 0.3, "snippet": "and Offline Character recognition and Offline character recognition further divided into two parts: - machine printed and handwritten character recognition [2]. Handwritten character recognition has many problems like different writing styles, variation in pen-tip, skewness in writing etc. OCR plays an important role in improvement of interface between computer and man [3]. Character recognition i"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 9, "score": 0.3267, "vector_score": 0.3949, "lexical_score": 0.2, "snippet": "128 features comprised of distance profiles. Second feature\nset was different histogram projection of size 190 and in last\nzonal density and background directional distribution forming\n144 features. These were applied on three classifiers names\nSVM, PNN and k -NN. The SVM was tested with radial basis\nkernel function. The different parameters were varied of each\nclassifier to get best results. SVM "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 12, "score": 0.2991, "vector_score": 0.4063, "lexical_score": 0.1, "snippet": "ross validation [1].\nIn [7] gradient information of an image is used as feature for the classification Gurmukhi characters and numerals. The two methods were proposed and both works on the blocks of an images. The information from each block was concatenated to form a single feature vector of dimensionality 2000. The method was tested on two different dataset each having 7000 and 2000 binary image"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 40, "score": 0.2973, "vector_score": 0.4035, "lexical_score": 0.1, "snippet": "racters and numerals. The two methods were proposed and both works on the blocks of an images. The information from each block was concatenated to form a single feature vector of dimensionality 2000. The method was tested on two different dataset each having 7000 and 2000 binary images. The recognition rate of Gurmukhi characters and numerals were found out to be 97.38% and 99.65%. The work was al"}]`

**Generated answer:**

One limitation mentioned near the end is the unique characteristics of the Gurmukhi script, such as the connectivity of characters on the headline, a large number of similar characters, and two or more characters in a word having intersecting minimum bounding rectangles. These characteristics pose significant challenges for machine printed character recognition.

- manual_score: 0
- manual_notes: Unsupported for 'near the end': it gives general script challenges from earlier content, not a near-end observation shown in the retrieved snippets.
