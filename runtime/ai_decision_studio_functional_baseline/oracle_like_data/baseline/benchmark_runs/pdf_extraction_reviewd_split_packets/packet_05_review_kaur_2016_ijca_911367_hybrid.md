# PDF Extraction Benchmark Review

Generated at: 2026-03-15 01:12:42
Provider: ollama · Model: qwen2.5:7b · Prompt profile: neutral

## How to use this review file

For each question, fill in:
- `manual_score`: 0, 1, or 2
- `manual_notes`: comments about answer quality, retrieval quality, and noise

---

Review packet: 05
Document: kaur-2016-ijca-911367.pdf
Mode: hybrid — Híbrido inteligente · pypdf + Docling seletivo
Questions in this packet: 16

### Mode: hybrid — Híbrido inteligente · pypdf + Docling seletivo

- Extraction time: 12.452 s
- Indexing time: 2.156 s
- Final characters: 19384
- Chunks: 20
- Docling mode: selective_pages
- Suspicious pages: [1]
- Pages processed with Docling: [1]

#### Question 1

**Question:** What main problem does the paper try to solve?

**Retrieval backend:** chroma
**Retrieval time:** 0.138 s
**Generation time:** 10.798 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 14, "score": 0.4423, "vector_score": 0.4785, "lexical_score": 0.375, "snippet": "omposing problem into multiple binary classes. The\ndiscrimination (separation) between classes is done by\nconstructing a hyper plane  [15]. The main goal is to find an\noptimal hyper plane  which expects to generalize the\ncomparison to th e others. The optimal hyper plane  is one\nwhich maximizes a measure of the “margin” between such\nclasses. The unknown data sample is then classified by the\nSVM ac"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 6, "score": 0.4404, "vector_score": 0.4756, "lexical_score": 0.375, "snippet": "ion Gurmukhi characters and numerals. The two\nmethods were proposed and both works on the blocks of an\nimages. The information from each block was concatenated to\nform a single feature vector of dimensionality 2000. The\nmethod was tested on two different dataset each having 7000\nand 2000 binary images. The recognition rate of Gurmukhi\ncharacters and numerals were found  out to be 97.38% and\n99.65%"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 4, "score": 0.3946, "vector_score": 0.4724, "lexical_score": 0.25, "snippet": "eat advancement in the field which are limited to the other  languages  like  English,  Arabic  and  Chinese  languages [4-6].\nIn  Punjabi,  most of the work is focused on online or offline handwritten character recognition and very little work is done for printed character recognition. So, in this paper an algorithm has been proposed for the recognition of Gurmukhi printed  character  recognition"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 10, "score": 0.3833, "vector_score": 0.4551, "lexical_score": 0.25, "snippet": "n\nfirst stage, characters were grouped into three sets on the basis\nof their position . In second, characters falling in middle zone\nset were further divided into smaller sets. In last stage, special\nfeatures were employed to distinguish the characters with the\nhelp of nearest neighbor classifier.\nAs we see, most of the work is done for han dwritten character\nrecognition and very little work is do"}]`

**Generated answer:**

The paper tries to solve the problem of printed Gurmukhi character recognition, which is relatively underexplored compared to handwritten recognition. Specifically, the paper addresses the challenge of creating an OCR (Optical Character Recognition) system for printed Gurmukhi characters across various font styles.

- manual_score: 1
- manual_notes: Correct main problem (printed Gurmukhi recognition) is supported, but “OCR system” and “across various font styles” are not clearly shown in the retrieved snippets.

#### Question 2

**Question:** What are the main contributions of the work?

**Retrieval backend:** chroma
**Retrieval time:** 0.44 s
**Generation time:** 16.487 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 4, "score": 0.4524, "vector_score": 0.4267, "lexical_score": 0.5, "snippet": "eat advancement in the field which are limited to the other  languages  like  English,  Arabic  and  Chinese  languages [4-6].\nIn  Punjabi,  most of the work is focused on online or offline handwritten character recognition and very little work is done for printed character recognition. So, in this paper an algorithm has been proposed for the recognition of Gurmukhi printed  character  recognition"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.4505, "vector_score": 0.4238, "lexical_score": 0.5, "snippet": "ided into subfields: - Online and Offline Character recognition and Offline character recognition further divided into  two  parts:  -  machine  printed  and  handwritten  character recognition  [2].  Handwritten  character  recognition  has  many problems  like  different  writing  styles,  variation  in  pen-tip, skewness  in  writing  etc.  OCR  plays  an  important  role  in improvement  of  i"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 17, "score": 0.4388, "vector_score": 0.4058, "lexical_score": 0.5, "snippet": "he results of C -SVC typ e of SVM are better than nu-SVC\ntype of SVM. Further, it is observed that highest accuracy of\n97.87% has been achieved from RBF kernel of nu-SVC type\nof SVM.\n5. CONCLUSION\nIn this paper printed character recognition system for\nGurumukhi is proposed. H ierarchical centroid method is used\nfor feature extraction  which does not require fixed size as\ncompared to existing work."}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.3837, "vector_score": 0.4108, "lexical_score": 0.3333, "snippet": "esearch  is devoted  to  online  and  offline  handwritten  character/script\n-·GT\n[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique "}]`

**Generated answer:**

The main contributions of the work described in this paper are:

1. **Proposed Algorithm for Printed Character Recognition**: The paper proposes an algorithm for recognizing Gurmukhi printed characters using a large set of different fonts.

2. **Feature Extraction Method**: Hierarchical centroid method is used for feature extraction, which does not require a fixed size as compared to existing work.

3. **Support Vector Machine (SVM) Classification**: The feature vector is learned for classification using SVM. The paper analyzes the performance using different combinations of SVM type and its kernels on a 10-fold cross-validation procedure.

4. **High Accuracy**: The highest accuracy obtained is 97.87% using the nu-SVC type of SVM with the RBF kernel.

5. **Future Work**: The paper suggests extending the work to handwritten Gurumukhi character recognition due to its high performance.

These contributions aim to improve the OCR system for the Gurmukhi language, which is an open and promising research topic, especially for the digitization of old and valuable Punjabi literature.

- manual_score: 1
- manual_notes: Partly supported: proposed system, hierarchical centroid features, SVM, and 97.87% are grounded, but the handwritten future-work claim and some broader context are unsupported.

#### Question 3

**Question:** What does Figure 1 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.212 s
**Generation time:** 7.82 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.3838, "vector_score": 0.4558, "lexical_score": 0.25, "snippet": "e  feature vector is give as: 2^d -1, where d is\nthe parametric value which denotes the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 12, "score": 0.3429, "vector_score": 0.393, "lexical_score": 0.25, "snippet": "Feature Extraction\nArmon [12] proposed a hierarchical centroid method for\nfeatures extraction from printed character images of Hebrew\nlanguage. The method is based on recursive subdivisions of\ninput binary image by measuring  centroids at each division\nand outputs a fixed length features vector. Further, feature\nvector are normalized according the size of the input image.\nTherefore the size of ima"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.2659, "vector_score": 0.4091, "lexical_score": 0.0, "snippet": "esearch  is devoted  to  online  and  offline  handwritten  character/script\n-·GT\n[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 7, "score": 0.2649, "vector_score": 0.4076, "lexical_score": 0.0, "snippet": "tree and nearest neighbor classifiers. The\nrecognition rate and processing speed are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap image"}]`

**Generated answer:**

The context provided does not contain any information about Figure 1. The details given are about feature extraction methods and classification techniques, but there is no mention of Figure 1. Therefore, I cannot provide what Figure 1 shows based on the given context.

- manual_score: 1
- manual_notes: Grounded refusal rather than a real answer; the visible snippets do not identify Figure 1, so retrieval appears insufficient.

#### Question 4

**Question:** What does Figure 3 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.173 s
**Generation time:** 6.962 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.3618, "vector_score": 0.422, "lexical_score": 0.25, "snippet": "e  feature vector is give as: 2^d -1, where d is\nthe parametric value which denotes the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 9, "score": 0.2709, "vector_score": 0.4167, "lexical_score": 0.0, "snippet": "with Gabor based features of dimensionality 200\n[10].\nThree different features and classifiers were tested for the\nrecognition of Gurmukhi characters from documents. In first,\n128 features comprised of distance profiles. Second feature\nset was different histogram projection of size 190 and in last\nzonal density and background directional distribution forming\n144 features. These were applied on thr"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 7, "score": 0.2523, "vector_score": 0.3882, "lexical_score": 0.0, "snippet": "tree and nearest neighbor classifiers. The\nrecognition rate and processing speed are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap image"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.2505, "vector_score": 0.3854, "lexical_score": 0.0, "snippet": "esearch  is devoted  to  online  and  offline  handwritten  character/script\n-·GT\n[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique "}]`

**Generated answer:**

The context provided does not contain any information about Figure 3. The details given are about feature extraction, classification techniques, and recognition rates for Gurmukhi characters, but there is no mention of Figure 3. Therefore, I cannot provide what Figure 3 shows based on the given context.

- manual_score: 1
- manual_notes: Grounded but incomplete: the retrieved snippets do not explicitly describe Figure 3, so the model declines instead of answering.

#### Question 5

**Question:** What does Figure 4 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.236 s
**Generation time:** 6.595 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.3666, "vector_score": 0.4294, "lexical_score": 0.25, "snippet": "e  feature vector is give as: 2^d -1, where d is\nthe parametric value which denotes the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.2538, "vector_score": 0.3904, "lexical_score": 0.0, "snippet": "esearch  is devoted  to  online  and  offline  handwritten  character/script\n-·GT\n[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 7, "score": 0.2536, "vector_score": 0.3902, "lexical_score": 0.0, "snippet": "tree and nearest neighbor classifiers. The\nrecognition rate and processing speed are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap image"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 20, "score": 0.2519, "vector_score": 0.3876, "lexical_score": 0.0, "snippet": "gnition and fast retrieval\nfor Hebrew historical manuscripts”, Master Thesis, 2011.\n[13] C. Cortes and V. Vapnik, “Support vector machine,”\nMachine learning, vol. 20, pp. 273-297, 1995\n[14] D. Singh, B. Singh, A new morphology based approach\nfor blood vessel segmentation in retinal images, in 2014\nAnnual IEEE India Conference (INDICON), 2014, pp. 1-\n6\nIJCATM : www.ijcaonline.org"}]`

**Generated answer:**

Figure 4 shows the divisions of the input image at different depth levels along the x-coordinate and y-coordinate. This figure is related to a recursive division process where the image is subdivided at various depth levels, with the divisions shown for Depth 1 to Depth 6 along both the x and y axes.

- manual_score: 1
- manual_notes: Partially supported by the depth/original-transposed diagram text, but the answer infers x/y-axis details and does not tie the content explicitly to Figure 4.

#### Question 6

**Question:** Which method or combination achieved the best performance?

**Retrieval backend:** chroma
**Retrieval time:** 0.256 s
**Generation time:** 8.557 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 17, "score": 0.6122, "vector_score": 0.4804, "lexical_score": 0.8571, "snippet": "he results of C -SVC typ e of SVM are better than nu-SVC\ntype of SVM. Further, it is observed that highest accuracy of\n97.87% has been achieved from RBF kernel of nu-SVC type\nof SVM.\n5. CONCLUSION\nIn this paper printed character recognition system for\nGurumukhi is proposed. H ierarchical centroid method is used\nfor feature extraction  which does not require fixed size as\ncompared to existing work."}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 7, "score": 0.5098, "vector_score": 0.4767, "lexical_score": 0.5714, "snippet": "tree and nearest neighbor classifiers. The\nrecognition rate and processing speed are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap image"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 8, "score": 0.4669, "vector_score": 0.4876, "lexical_score": 0.4286, "snippet": "age group.\nThree strategies w ere formed by dividing the whole dataset\ninto the different propositions which were further used as the\ntraining and testing. Two features were extracted from each\nimages and tested on the two classifiers SVM and k -NN.\nLinear and polynomial kernel function s were applied in case\nof SVM and k -NN were tested with 1, 3, 5 and 7 as different\nvalues for k [9].\nThe datase"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 15, "score": 0.4501, "vector_score": 0.4616, "lexical_score": 0.4286, "snippet": "g and testing. The\nefficiency of proposed classifier is obtained by using n-fold\ncross validation procedure. In this approach, initially the\n[Página 4]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n27\ndataset of size P is divid ed into n disjoint groups known as\ntest sets. Then the classifier is trained on rest of data by\nremoving one test set. The "}]`

**Generated answer:**

The combination of nu-SVC type of SVM with the RBF kernel achieved the highest accuracy of 97.87% in the proposed printed character recognition system for Gurumukhi. This result is based on the 10-fold cross-validation procedure described in the paper.

- manual_score: 2
- manual_notes: Correct and well supported: the snippets explicitly say the highest accuracy was 97.87% with the RBF kernel of nu-SVC.

#### Question 7

**Question:** Which evaluation metric was used?

**Retrieval backend:** chroma
**Retrieval time:** 0.198 s
**Generation time:** 8.759 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 8, "score": 0.5488, "vector_score": 0.5213, "lexical_score": 0.6, "snippet": "age group.\nThree strategies w ere formed by dividing the whole dataset\ninto the different propositions which were further used as the\ntraining and testing. Two features were extracted from each\nimages and tested on the two classifiers SVM and k -NN.\nLinear and polynomial kernel function s were applied in case\nof SVM and k -NN were tested with 1, 3, 5 and 7 as different\nvalues for k [9].\nThe datase"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 7, "score": 0.5405, "vector_score": 0.5085, "lexical_score": 0.6, "snippet": "tree and nearest neighbor classifiers. The\nrecognition rate and processing speed are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap image"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.501, "vector_score": 0.4477, "lexical_score": 0.6, "snippet": "e  feature vector is give as: 2^d -1, where d is\nthe parametric value which denotes the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 9, "score": 0.4689, "vector_score": 0.506, "lexical_score": 0.4, "snippet": "with Gabor based features of dimensionality 200\n[10].\nThree different features and classifiers were tested for the\nrecognition of Gurmukhi characters from documents. In first,\n128 features comprised of distance profiles. Second feature\nset was different histogram projection of size 190 and in last\nzonal density and background directional distribution forming\n144 features. These were applied on thr"}]`

**Generated answer:**

Based on the context provided, the evaluation metric used was accuracy. Specifically, the methodology achieved 94.29% accuracy in Gurmukhi script classification using Gabor based features. Additionally, another study reported an accuracy of 94.12% using a combination of horizontal and vertical projection features with k-NN and SVM classifiers.

- manual_score: 1
- manual_notes: Likely correct that the metric is accuracy, but the answer mixes in unrelated prior-study numbers and is weakly grounded in the provided snippets.

#### Question 8

**Question:** What does the main results table compare?

**Retrieval backend:** chroma
**Retrieval time:** 0.249 s
**Generation time:** 10.072 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.4542, "vector_score": 0.468, "lexical_score": 0.4286, "snippet": "e  feature vector is give as: 2^d -1, where d is\nthe parametric value which denotes the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 14, "score": 0.4461, "vector_score": 0.4555, "lexical_score": 0.4286, "snippet": "omposing problem into multiple binary classes. The\ndiscrimination (separation) between classes is done by\nconstructing a hyper plane  [15]. The main goal is to find an\noptimal hyper plane  which expects to generalize the\ncomparison to th e others. The optimal hyper plane  is one\nwhich maximizes a measure of the “margin” between such\nclasses. The unknown data sample is then classified by the\nSVM ac"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 16, "score": 0.4064, "vector_score": 0.3944, "lexical_score": 0.4286, "snippet": "osed character recognition system needs to cl assify\nthe Gurumukhi characters into 45 different classes of\ncharacters including 35 alphabets and ten  numeric characters.\nA multiclass SVM classifier tool LIBSVM (A Library for\nSupport Vector Machines) has been used in this study.\nThe performance of classification on LIBSVM tool is\nmeasured by considering two types of SVM namely, C -SVC\nand nu-SVC an"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 17, "score": 0.4053, "vector_score": 0.3928, "lexical_score": 0.4286, "snippet": "he results of C -SVC typ e of SVM are better than nu-SVC\ntype of SVM. Further, it is observed that highest accuracy of\n97.87% has been achieved from RBF kernel of nu-SVC type\nof SVM.\n5. CONCLUSION\nIn this paper printed character recognition system for\nGurumukhi is proposed. H ierarchical centroid method is used\nfor feature extraction  which does not require fixed size as\ncompared to existing work."}]`

**Generated answer:**

The main results table compares the classification accuracy obtained using different types of Support Vector Machine (SVM) and kernel functions. Specifically, it compares:

1. Two types of SVM: nu-SVC and C-SVC
2. Three types of kernels: Gaussian RBF (Radial Basis Function) kernel, Linear Kernel, and Polynomial kernel

The table shows the accuracy percentages for each combination of SVM type and kernel function.

- manual_score: 2
- manual_notes: Correct and supported: the snippets indicate the results compare classification performance across SVM types (C-SVC vs nu-SVC) and kernel choices.

#### Question 9

**Question:** What limitations or future work are mentioned?

**Retrieval backend:** chroma
**Retrieval time:** 0.289 s
**Generation time:** 11.065 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 4, "score": 0.4094, "vector_score": 0.4504, "lexical_score": 0.3333, "snippet": "eat advancement in the field which are limited to the other  languages  like  English,  Arabic  and  Chinese  languages [4-6].\nIn  Punjabi,  most of the work is focused on online or offline handwritten character recognition and very little work is done for printed character recognition. So, in this paper an algorithm has been proposed for the recognition of Gurmukhi printed  character  recognition"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 6, "score": 0.3955, "vector_score": 0.429, "lexical_score": 0.3333, "snippet": "ion Gurmukhi characters and numerals. The two\nmethods were proposed and both works on the blocks of an\nimages. The information from each block was concatenated to\nform a single feature vector of dimensionality 2000. The\nmethod was tested on two different dataset each having 7000\nand 2000 binary images. The recognition rate of Gurmukhi\ncharacters and numerals were found  out to be 97.38% and\n99.65%"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.3936, "vector_score": 0.426, "lexical_score": 0.3333, "snippet": "ided into subfields: - Online and Offline Character recognition and Offline character recognition further divided into  two  parts:  -  machine  printed  and  handwritten  character recognition  [2].  Handwritten  character  recognition  has  many problems  like  different  writing  styles,  variation  in  pen-tip, skewness  in  writing  etc.  OCR  plays  an  important  role  in improvement  of  i"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 7, "score": 0.3845, "vector_score": 0.4121, "lexical_score": 0.3333, "snippet": "tree and nearest neighbor classifiers. The\nrecognition rate and processing speed are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap image"}]`

**Generated answer:**

Based on the provided context, there are no explicit mentions of specific limitations or future work. The text primarily discusses the current state of research in Gurmukhi character recognition, focusing on the limitations in the field, particularly for printed characters in Punjabi, and the advancements made in handwritten character recognition. However, it does not outline any specific limitations or suggest future work to be done. 

If you need more detailed information on limitations or future work, you might need to look for additional sections or references in the full paper that are not included in the provided context.

- manual_score: 1
- manual_notes: Conservative and grounded in the weak retrieval, but it does not provide a concrete limitation/future-work item from the paper.

#### Question 10

**Question:** At a high level, how does the method work based on both the text and the figures?

**Retrieval backend:** chroma
**Retrieval time:** 0.246 s
**Generation time:** 22.032 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 12, "score": 0.514, "vector_score": 0.5664, "lexical_score": 0.4167, "snippet": "Feature Extraction\nArmon [12] proposed a hierarchical centroid method for\nfeatures extraction from printed character images of Hebrew\nlanguage. The method is based on recursive subdivisions of\ninput binary image by measuring  centroids at each division\nand outputs a fixed length features vector. Further, feature\nvector are normalized according the size of the input image.\nTherefore the size of ima"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 6, "score": 0.486, "vector_score": 0.5233, "lexical_score": 0.4167, "snippet": "ion Gurmukhi characters and numerals. The two\nmethods were proposed and both works on the blocks of an\nimages. The information from each block was concatenated to\nform a single feature vector of dimensionality 2000. The\nmethod was tested on two different dataset each having 7000\nand 2000 binary images. The recognition rate of Gurmukhi\ncharacters and numerals were found  out to be 97.38% and\n99.65%"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.4756, "vector_score": 0.5522, "lexical_score": 0.3333, "snippet": "esearch  is devoted  to  online  and  offline  handwritten  character/script\n-·GT\n[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 8, "score": 0.4749, "vector_score": 0.5511, "lexical_score": 0.3333, "snippet": "age group.\nThree strategies w ere formed by dividing the whole dataset\ninto the different propositions which were further used as the\ntraining and testing. Two features were extracted from each\nimages and tested on the two classifiers SVM and k -NN.\nLinear and polynomial kernel function s were applied in case\nof SVM and k -NN were tested with 1, 3, 5 and 7 as different\nvalues for k [9].\nThe datase"}]`

**Generated answer:**

Based on the provided context, the hierarchical centroid method for feature extraction from Hebrew character images works as follows:

1. **Hierarchical Subdivision**: The method recursively subdivides the input binary image. At each division, centroids are calculated to measure the distribution of pixels.

2. **Feature Vector Construction**: The method outputs a fixed-length feature vector. The length of this vector is given by \(2^d - 1\), where \(d\) is the recursive depth or number of divisions.

3. **Normalization**: The feature vectors are normalized according to the size of the input image. This ensures that the size of the images does not affect the final feature set.

4. **Two-Step Procedure**: The feature extraction process is divided into two steps:
   - **First Step (X-Coordinate)**: The first-order moment (center of mass) is calculated for the x-coordinate. The image is then divided into two sub-images by the x-coordinate. This process is repeated recursively for the newly generated sub-images.
   - **Second Step (Y-Coordinate)**: The process is repeated for the y-coordinate, but with the sub-images transposed.

5. **Recursive Depth**: The method produces subdivisions along one axis twice as much as the other, which affects the feature vector length.

Unfortunately, the context does not provide specific details about figures or how the method works at a high level based on figures. If there were figures, they would likely illustrate the recursive subdivision process and the calculation of centroids at each step. However, based on the text, the method focuses on hierarchical division and centroid calculation without explicit mention of figures.

For a more detailed understanding, it would be helpful to review any relevant figures that might accompany the text.

- manual_score: 1
- manual_notes: Mostly grounded summary of hierarchical centroid feature extraction, but incomplete for the full method and partly framed through the cited Hebrew-method description rather than the paper’s full pipeline.

#### Question 11

**Question:** What is the central topic of the document?

**Retrieval backend:** chroma
**Retrieval time:** 0.284 s
**Generation time:** 9.653 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.4242, "vector_score": 0.4372, "lexical_score": 0.4, "snippet": "ided into subfields: - Online and Offline Character recognition and Offline character recognition further divided into  two  parts:  -  machine  printed  and  handwritten  character recognition  [2].  Handwritten  character  recognition  has  many problems  like  different  writing  styles,  variation  in  pen-tip, skewness  in  writing  etc.  OCR  plays  an  important  role  in improvement  of  i"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 2, "score": 0.4159, "vector_score": 0.4245, "lexical_score": 0.4, "snippet": "Machine, Printed Gurmukhi.\n## 1. INTRODUCTION\nMultiple languages are used among different people in India which mainly depends on their geographical locations. Gurmukhi  is  one  of  the  languages  which  is  mostly  used  in northern region of India. This script was devised by first Sikh Guru, Sri Guru Nanak Dev ji in 16th century and popularized by second Sikh Guru, Sri Guru Angad Dev ji. Gurmu"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 17, "score": 0.3445, "vector_score": 0.4223, "lexical_score": 0.2, "snippet": "he results of C -SVC typ e of SVM are better than nu-SVC\ntype of SVM. Further, it is observed that highest accuracy of\n97.87% has been achieved from RBF kernel of nu-SVC type\nof SVM.\n5. CONCLUSION\nIn this paper printed character recognition system for\nGurumukhi is proposed. H ierarchical centroid method is used\nfor feature extraction  which does not require fixed size as\ncompared to existing work."}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.3425, "vector_score": 0.4193, "lexical_score": 0.2, "snippet": "[Página 1]\n· ST\n0\n5\n1\n2\n8\n## Gurmukhi Printed Character Recognition using Hierarchical Centroid Method and SVM 7\nSandeep Kaur Punjabi University Regional Centre for IT &amp; Mgmt. Mohali, India\n## ABSTRACT\nIn this paper  the system  for the recognition of printed Gurmukhi character is proposed. Hierarchical centroid method  is  used  for  extracting  the  feature  from  images  of printed characte"}]`

**Generated answer:**

The central topic of the document is the recognition of printed Gurmukhi characters using a hierarchical centroid method and Support Vector Machine (SVM) classification. Specifically, the document describes a system for recognizing printed Gurmukhi characters, focusing on the use of hierarchical centroid method for feature extraction and SVM for classification. The highest accuracy achieved with this system is 97.87%.

- manual_score: 2
- manual_notes: Correct and well supported by the title/abstract/conclusion snippets: the paper is about printed Gurmukhi character recognition using hierarchical centroid features and SVM.

#### Question 12

**Question:** What are the 3 most important sections or takeaways?

**Retrieval backend:** chroma
**Retrieval time:** 0.265 s
**Generation time:** 13.351 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.4793, "vector_score": 0.4297, "lexical_score": 0.5714, "snippet": "ided into subfields: - Online and Offline Character recognition and Offline character recognition further divided into  two  parts:  -  machine  printed  and  handwritten  character recognition  [2].  Handwritten  character  recognition  has  many problems  like  different  writing  styles,  variation  in  pen-tip, skewness  in  writing  etc.  OCR  plays  an  important  role  in improvement  of  i"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 12, "score": 0.3692, "vector_score": 0.4142, "lexical_score": 0.2857, "snippet": "Feature Extraction\nArmon [12] proposed a hierarchical centroid method for\nfeatures extraction from printed character images of Hebrew\nlanguage. The method is based on recursive subdivisions of\ninput binary image by measuring  centroids at each division\nand outputs a fixed length features vector. Further, feature\nvector are normalized according the size of the input image.\nTherefore the size of ima"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 7, "score": 0.3631, "vector_score": 0.4048, "lexical_score": 0.2857, "snippet": "tree and nearest neighbor classifiers. The\nrecognition rate and processing speed are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap image"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 6, "score": 0.3567, "vector_score": 0.3949, "lexical_score": 0.2857, "snippet": "ion Gurmukhi characters and numerals. The two\nmethods were proposed and both works on the blocks of an\nimages. The information from each block was concatenated to\nform a single feature vector of dimensionality 2000. The\nmethod was tested on two different dataset each having 7000\nand 2000 binary images. The recognition rate of Gurmukhi\ncharacters and numerals were found  out to be 97.38% and\n99.65%"}]`

**Generated answer:**

Based on the provided context, here are three important sections or takeaways:

1. **Character Recognition Subfields**: Character recognition is divided into online and offline recognition, with offline recognition further divided into machine-printed and handwritten. Handwritten character recognition faces challenges such as varying writing styles and pen-tip variations.

2. **Punjabi Language OCR**: The recognition of the Punjabi language, which uses the Gurmukhi script, is highlighted as an important research topic. This is due to the language's wide usage and the potential for digitizing old and valuable literature, which could aid in its conservation.

3. **Feature Extraction Methods**: For Gurmukhi character recognition, various feature extraction methods are discussed. These include hierarchical centroid methods, skeleton-based feature extraction, and block-based feature extraction. These methods aim to improve recognition rates and processing speeds, with some achieving high accuracy rates like 96.6% recognition rate and 175 characters per second.

- manual_score: 1
- manual_notes: Plausible takeaways, but they are broad and partly drawn from generic/related-work context rather than clearly identified as the three main takeaways of this paper.

#### Question 13

**Question:** Does the document contain tables? What do they show?

**Retrieval backend:** chroma
**Retrieval time:** 0.267 s
**Generation time:** 8.892 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 11, "score": 0.374, "vector_score": 0.4408, "lexical_score": 0.25, "snippet": "aracter of every style is printed in\nthree font sizes of 18, 24 and 30. There are total 35 characters\nin Punjabi and 10  numerals. So a dataset of 3915 images is\ncreated in the proposed study. Size of images varies from\n20*21 pixels to 40*41 pixels with a bit depth of 1. The sample\nimages of font styles used in our dataset are shown in Figure\n3.\nStyle name Fonts sample\nAdami\nRangdar\nAdhiapak\nFig. "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.3411, "vector_score": 0.4574, "lexical_score": 0.125, "snippet": "esearch  is devoted  to  online  and  offline  handwritten  character/script\n-·GT\n[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.3257, "vector_score": 0.4337, "lexical_score": 0.125, "snippet": "e  feature vector is give as: 2^d -1, where d is\nthe parametric value which denotes the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 4, "score": 0.3238, "vector_score": 0.4308, "lexical_score": 0.125, "snippet": "eat advancement in the field which are limited to the other  languages  like  English,  Arabic  and  Chinese  languages [4-6].\nIn  Punjabi,  most of the work is focused on online or offline handwritten character recognition and very little work is done for printed character recognition. So, in this paper an algorithm has been proposed for the recognition of Gurmukhi printed  character  recognition"}]`

**Generated answer:**

The provided context does not contain any tables. The information is presented in text form, describing the methodology, features, and classification process for recognizing Punjabi printed characters. There are references to figures (e.g., Figure 3, Figure 4), but no tables are mentioned or described in the given text.

- manual_score: 1
- manual_notes: Conservative but weak: no explicit table is identified, yet the snippets include table-like font-style content, so the claim that there are no tables is not fully secure.

#### Question 14

**Question:** Does the document contain figures or diagrams? What do they show?

**Retrieval backend:** chroma
**Retrieval time:** 0.263 s
**Generation time:** 6.892 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 11, "score": 0.369, "vector_score": 0.448, "lexical_score": 0.2222, "snippet": "aracter of every style is printed in\nthree font sizes of 18, 24 and 30. There are total 35 characters\nin Punjabi and 10  numerals. So a dataset of 3915 images is\ncreated in the proposed study. Size of images varies from\n20*21 pixels to 40*41 pixels with a bit depth of 1. The sample\nimages of font styles used in our dataset are shown in Figure\n3.\nStyle name Fonts sample\nAdami\nRangdar\nAdhiapak\nFig. "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 17, "score": 0.358, "vector_score": 0.4311, "lexical_score": 0.2222, "snippet": "he results of C -SVC typ e of SVM are better than nu-SVC\ntype of SVM. Further, it is observed that highest accuracy of\n97.87% has been achieved from RBF kernel of nu-SVC type\nof SVM.\n5. CONCLUSION\nIn this paper printed character recognition system for\nGurumukhi is proposed. H ierarchical centroid method is used\nfor feature extraction  which does not require fixed size as\ncompared to existing work."}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.3507, "vector_score": 0.4797, "lexical_score": 0.1111, "snippet": "esearch  is devoted  to  online  and  offline  handwritten  character/script\n-·GT\n[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 7, "score": 0.3307, "vector_score": 0.449, "lexical_score": 0.1111, "snippet": "tree and nearest neighbor classifiers. The\nrecognition rate and processing speed are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap image"}]`

**Generated answer:**

Yes, the document contains figures. Specifically, it mentions Figure 3, which shows "Sample Font Styles of our Dataset". This figure displays examples of different font styles used in the dataset, including Adami, Rangdar, and Adhiapak.

- manual_score: 2
- manual_notes: Correct and supported: the snippets explicitly mention Figure 3 showing sample font styles used in the dataset.

#### Question 15

**Question:** What is one important piece of information from the middle of the document?

**Retrieval backend:** chroma
**Retrieval time:** 0.146 s
**Generation time:** 8.269 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 2, "score": 0.453, "vector_score": 0.4577, "lexical_score": 0.4444, "snippet": "Machine, Printed Gurmukhi.\n## 1. INTRODUCTION\nMultiple languages are used among different people in India which mainly depends on their geographical locations. Gurmukhi  is  one  of  the  languages  which  is  mostly  used  in northern region of India. This script was devised by first Sikh Guru, Sri Guru Nanak Dev ji in 16th century and popularized by second Sikh Guru, Sri Guru Angad Dev ji. Gurmu"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.4094, "vector_score": 0.4504, "lexical_score": 0.3333, "snippet": "ided into subfields: - Online and Offline Character recognition and Offline character recognition further divided into  two  parts:  -  machine  printed  and  handwritten  character recognition  [2].  Handwritten  character  recognition  has  many problems  like  different  writing  styles,  variation  in  pen-tip, skewness  in  writing  etc.  OCR  plays  an  important  role  in improvement  of  i"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.4054, "vector_score": 0.4443, "lexical_score": 0.3333, "snippet": "esearch  is devoted  to  online  and  offline  handwritten  character/script\n-·GT\n[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 12, "score": 0.398, "vector_score": 0.4328, "lexical_score": 0.3333, "snippet": "Feature Extraction\nArmon [12] proposed a hierarchical centroid method for\nfeatures extraction from printed character images of Hebrew\nlanguage. The method is based on recursive subdivisions of\ninput binary image by measuring  centroids at each division\nand outputs a fixed length features vector. Further, feature\nvector are normalized according the size of the input image.\nTherefore the size of ima"}]`

**Generated answer:**

One important piece of information from the middle of the document is that Optical Character Recognition (OCR) plays an important role in improving the interface between computers and humans. This highlights the significance of OCR technology in making documents machine-readable, which can enhance accessibility and processing of written information.

- manual_score: 1
- manual_notes: Supported by the intro snippet, but generic and not clearly “from the middle of the document”; a more specific mid-document point was available.

#### Question 16

**Question:** What is one limitation, note, or important observation mentioned near the end?

**Retrieval backend:** chroma
**Retrieval time:** 0.163 s
**Generation time:** 8.255 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.3644, "vector_score": 0.3991, "lexical_score": 0.3, "snippet": "ided into subfields: - Online and Offline Character recognition and Offline character recognition further divided into  two  parts:  -  machine  printed  and  handwritten  character recognition  [2].  Handwritten  character  recognition  has  many problems  like  different  writing  styles,  variation  in  pen-tip, skewness  in  writing  etc.  OCR  plays  an  important  role  in improvement  of  i"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 12, "score": 0.3275, "vector_score": 0.3962, "lexical_score": 0.2, "snippet": "Feature Extraction\nArmon [12] proposed a hierarchical centroid method for\nfeatures extraction from printed character images of Hebrew\nlanguage. The method is based on recursive subdivisions of\ninput binary image by measuring  centroids at each division\nand outputs a fixed length features vector. Further, feature\nvector are normalized according the size of the input image.\nTherefore the size of ima"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.3251, "vector_score": 0.3925, "lexical_score": 0.2, "snippet": "e  feature vector is give as: 2^d -1, where d is\nthe parametric value which denotes the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 6, "score": 0.3011, "vector_score": 0.4094, "lexical_score": 0.1, "snippet": "ion Gurmukhi characters and numerals. The two\nmethods were proposed and both works on the blocks of an\nimages. The information from each block was concatenated to\nform a single feature vector of dimensionality 2000. The\nmethod was tested on two different dataset each having 7000\nand 2000 binary images. The recognition rate of Gurmukhi\ncharacters and numerals were found  out to be 97.38% and\n99.65%"}]`

**Generated answer:**

One limitation mentioned near the end is that the segmentation algorithm breaks sentences into characters and then recognition takes place. This process faces challenges, particularly with the connectivity of characters on the headline, a large number of similar characters, and two or more characters in a word having intersecting minimum bounding rectangles.

- manual_score: 0
- manual_notes: Unsupported/hallucinated: the cited snippets do not mention segmentation, headlines, or intersecting bounding rectangles.
