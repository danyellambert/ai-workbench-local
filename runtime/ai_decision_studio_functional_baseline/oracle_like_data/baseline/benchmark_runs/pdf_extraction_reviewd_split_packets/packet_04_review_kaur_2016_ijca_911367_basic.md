# PDF Extraction Benchmark Review

Generated at: 2026-03-15 01:12:42
Provider: ollama · Model: qwen2.5:7b · Prompt profile: neutral

## How to use this review file

For each question, fill in:
- `manual_score`: 0, 1, or 2
- `manual_notes`: comments about answer quality, retrieval quality, and noise

---

Review packet: 04
Document: kaur-2016-ijca-911367.pdf
Mode: basic — Básico · pypdf apenas · mais rápido
Questions in this packet: 16

### Mode: basic — Básico · pypdf apenas · mais rápido

- Extraction time: 0.09 s
- Indexing time: 1.662 s
- Final characters: 15301
- Chunks: 16
- Docling mode: none
- Suspicious pages: [1]
- Pages processed with Docling: []

#### Question 1

**Question:** What main problem does the paper try to solve?

**Retrieval backend:** chroma
**Retrieval time:** 0.124 s
**Generation time:** 10.433 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 2, "score": 0.4317, "vector_score": 0.4623, "lexical_score": 0.375, "snippet": "on the blocks of an\nimages. The information from each block was concatenated to\nform a single feature vector of dimensionality 2000. The\nmethod was tested on two different dataset each having 7000\nand 2000 binary images. The recognition rate of Gurmukhi\ncharacters and numerals were found  out to be 97.38% and\n99.65%. The work was also extended to find out collective\naccuracy of methodology for bot"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 9, "score": 0.4156, "vector_score": 0.4374, "lexical_score": 0.375, "snippet": "s the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x a"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.4131, "vector_score": 0.4336, "lexical_score": 0.375, "snippet": "is observed that highest accuracy of\n97.87% has been achieved from RBF kernel of nu-SVC type\nof SVM.\n5. CONCLUSION\nIn this paper printed character recognition system for\nGurumukhi is proposed. H ierarchical centroid method is used\nfor feature extraction  which does not require fixed size as\ncompared to existing work. The obtained feature vector is\nthen learned for classification using Support Vect"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 10, "score": 0.3846, "vector_score": 0.457, "lexical_score": 0.25, "snippet": "ween classes is done by\nconstructing a hyper plane  [15]. The main goal is to find an\noptimal hyper plane  which expects to generalize the\ncomparison to th e others. The optimal hyper plane  is one\nwhich maximizes a measure of the “margin” between such\nclasses. The unknown data sample is then classified by the\nSVM according to the decision boundaries defined by these\nhyper planes . Hyper planes  w"}]`

**Generated answer:**

The main problem the paper tries to solve is the recognition of Gurmukhi script characters and numerals, particularly focusing on machine-printed characters. The paper mentions specific challenges in Gurmukhi script recognition, such as:

- Unique characteristics of the script like connectivity of characters on the headline.
- A large number of similar characters.
- Two or more characters in a word having intersecting minimum bounding rectangles.

These issues make the recognition task more complex and error-prone.

- manual_score: 1
- manual_notes: Core claim (printed Gurmukhi character/numeral recognition) is supported, but the listed script challenges are not shown in Top sources.

#### Question 2

**Question:** What are the main contributions of the work?

**Retrieval backend:** chroma
**Retrieval time:** 0.158 s
**Generation time:** 21.688 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.4342, "vector_score": 0.3987, "lexical_score": 0.5, "snippet": "are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap images of the characters and then Euclidean\ndistance between the testing point and ref"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 10, "score": 0.4282, "vector_score": 0.3895, "lexical_score": 0.5, "snippet": "ween classes is done by\nconstructing a hyper plane  [15]. The main goal is to find an\noptimal hyper plane  which expects to generalize the\ncomparison to th e others. The optimal hyper plane  is one\nwhich maximizes a measure of the “margin” between such\nclasses. The unknown data sample is then classified by the\nSVM according to the decision boundaries defined by these\nhyper planes . Hyper planes  w"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.3833, "vector_score": 0.4102, "lexical_score": 0.3333, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.3831, "vector_score": 0.4099, "lexical_score": 0.3333, "snippet": "is observed that highest accuracy of\n97.87% has been achieved from RBF kernel of nu-SVC type\nof SVM.\n5. CONCLUSION\nIn this paper printed character recognition system for\nGurumukhi is proposed. H ierarchical centroid method is used\nfor feature extraction  which does not require fixed size as\ncompared to existing work. The obtained feature vector is\nthen learned for classification using Support Vect"}]`

**Generated answer:**

The main contributions of the work, as described in the context, include:

1. **Feature Extraction and Classification Method**: The work employs a combination of horizontal and vertical projection-based features along with k-NN and SVM classifiers for the recognition of Gurmukhi script. This approach uses a dataset of 3500 samples collected from 10 different people, each belonging to a different age group.

2. **Dataset Utilization**: The dataset is divided into different propositions to form three strategies, which are further used for training and testing. Two features are extracted from each image and tested on both SVM and k-NN classifiers.

3. **Kernel Functions**: The study uses linear and polynomial kernel functions in the SVM classifier, and it observes that the RBF kernel of nu-SVC type achieves the highest accuracy of 97.87%.

4. **Cross-Validation**: The classification is done using a n-fold cross-validation procedure, specifically a 10-fold cross-validation, to ensure the efficiency and robustness of the proposed classifier.

5. **Hierarchical Centroid Method**: While not the main focus, the paper mentions the use of the hierarchical centroid method for feature extraction, which is noted for its flexibility compared to existing methods.

6. **High Accuracy**: The system achieves a high accuracy of 97.87% with the combination of nu-SVC type and RBF kernel, which is a significant contribution to the field of Gurmukhi character recognition.

These contributions highlight the effectiveness of the proposed method in recognizing Gurmukhi characters with high accuracy, making it a valuable addition to the existing literature on character recognition systems.

- manual_score: 0
- manual_notes: Mostly unsupported/confused with prior-work snippets; only hierarchical centroid + SVM + 97.87% are grounded.

#### Question 3

**Question:** What does Figure 1 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.234 s
**Generation time:** 7.078 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 9, "score": 0.366, "vector_score": 0.4284, "lexical_score": 0.25, "snippet": "s the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x a"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 8, "score": 0.3361, "vector_score": 0.3825, "lexical_score": 0.25, "snippet": "extraction from printed character images of Hebrew\nlanguage. The method is based on recursive subdivisions of\ninput binary image by measuring  centroids at each division\nand outputs a fixed length features vector. Further, feature\nvector are normalized according the size of the input image.\nTherefore the size of images does not affect the final feature\nset. The method is a two -step procedure in w"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.2749, "vector_score": 0.4229, "lexical_score": 0.0, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 16, "score": 0.2646, "vector_score": 0.407, "lexical_score": 0.0, "snippet": ".\n[13] C. Cortes and V. Vapnik, “Support vector machine,”\nMachine learning, vol. 20, pp. 273-297, 1995\n[14] D. Singh, B. Singh, A new morphology based approach\nfor blood vessel segmentation in retinal images, in 2014\nAnnual IEEE India Conference (INDICON), 2014, pp. 1-\n6\nIJCATM : www.ijcaonline.org"}]`

**Generated answer:**

The context provided does not contain any information about Figure 1. The details given are about feature extraction and classification methods, but there is no mention of Figure 1. Therefore, I cannot provide what Figure 1 shows based on the given information.

- manual_score: 2
- manual_notes: Top sources do not mention Figure 1; answer correctly states the retrieval lacks evidence.

#### Question 4

**Question:** What does Figure 3 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.226 s
**Generation time:** 6.97 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 9, "score": 0.3465, "vector_score": 0.3985, "lexical_score": 0.25, "snippet": "s the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x a"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.2741, "vector_score": 0.4217, "lexical_score": 0.0, "snippet": "classifiers were tested for the\nrecognition of Gurmukhi characters from documents. In first,\n128 features comprised of distance profiles. Second feature\nset was different histogram projection of size 190 and in last\nzonal density and background directional distribution forming\n144 features. These were applied on three classifiers names\nSVM, PNN and k -NN. The SVM was tested with radial basis\nkerne"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.2554, "vector_score": 0.3929, "lexical_score": 0.0, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.2427, "vector_score": 0.3734, "lexical_score": 0.0, "snippet": "are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap images of the characters and then Euclidean\ndistance between the testing point and ref"}]`

**Generated answer:**

The context provided does not contain any information about Figure 3. The details given are about feature extraction, classification techniques, and recognition accuracy for Gurmukhi characters, but there is no mention of Figure 3. Therefore, I cannot provide what Figure 3 shows based on the given context.

- manual_score: 2
- manual_notes: Top sources do not mention Figure 3; answer is faithful to missing evidence, though retrieval is poor.

#### Question 5

**Question:** What does Figure 4 show?

**Retrieval backend:** chroma
**Retrieval time:** 0.224 s
**Generation time:** 7.18 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 9, "score": 0.3553, "vector_score": 0.412, "lexical_score": 0.25, "snippet": "s the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x a"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.256, "vector_score": 0.3939, "lexical_score": 0.0, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 16, "score": 0.2535, "vector_score": 0.39, "lexical_score": 0.0, "snippet": ".\n[13] C. Cortes and V. Vapnik, “Support vector machine,”\nMachine learning, vol. 20, pp. 273-297, 1995\n[14] D. Singh, B. Singh, A new morphology based approach\nfor blood vessel segmentation in retinal images, in 2014\nAnnual IEEE India Conference (INDICON), 2014, pp. 1-\n6\nIJCATM : www.ijcaonline.org"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.2482, "vector_score": 0.3819, "lexical_score": 0.0, "snippet": "classifiers were tested for the\nrecognition of Gurmukhi characters from documents. In first,\n128 features comprised of distance profiles. Second feature\nset was different histogram projection of size 190 and in last\nzonal density and background directional distribution forming\n144 features. These were applied on three classifiers names\nSVM, PNN and k -NN. The SVM was tested with radial basis\nkerne"}]`

**Generated answer:**

Figure 4 shows the divisions of the input image at different depth levels along the x-coordinate and y-coordinate. Specifically, it illustrates how the image is divided recursively at various depth levels, with subdivisions occurring twice as much along one axis compared to others. This figure helps in understanding the structure and depth levels used in the feature extraction process for the Gurmukhi character recognition technique described in the text.

- manual_score: 2
- manual_notes: Correctly grounded in the Fig. 4 snippet about recursive depth-level divisions; only minor paraphrase.

#### Question 6

**Question:** Which method or combination achieved the best performance?

**Retrieval backend:** chroma
**Retrieval time:** 0.163 s
**Generation time:** 8.964 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.6156, "vector_score": 0.4856, "lexical_score": 0.8571, "snippet": "is observed that highest accuracy of\n97.87% has been achieved from RBF kernel of nu-SVC type\nof SVM.\n5. CONCLUSION\nIn this paper printed character recognition system for\nGurumukhi is proposed. H ierarchical centroid method is used\nfor feature extraction  which does not require fixed size as\ncompared to existing work. The obtained feature vector is\nthen learned for classification using Support Vect"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.5128, "vector_score": 0.4813, "lexical_score": 0.5714, "snippet": "are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap images of the characters and then Euclidean\ndistance between the testing point and ref"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 4, "score": 0.4638, "vector_score": 0.4828, "lexical_score": 0.4286, "snippet": "fferent propositions which were further used as the\ntraining and testing. Two features were extracted from each\nimages and tested on the two classifiers SVM and k -NN.\nLinear and polynomial kernel function s were applied in case\nof SVM and k -NN were tested with 1, 3, 5 and 7 as different\nvalues for k [9].\nThe dataset consist of 7000 images of same size were\ncollected from 20 writers of different "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.4411, "vector_score": 0.4478, "lexical_score": 0.4286, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}]`

**Generated answer:**

The combination of nu-SVC type and RBF kernel achieved the highest accuracy of 97.87% in the proposed printed character recognition system for Gurumukhi. This result is from the hierarchical centroid method used for feature extraction and Support Vector Machine (SVM) classification on a dataset with varying font sizes and types.

- manual_score: 2
- manual_notes: Correct and supported: nu-SVC with the RBF kernel achieved the best result (97.87%); extra detail is minor.

#### Question 7

**Question:** Which evaluation metric was used?

**Retrieval backend:** chroma
**Retrieval time:** 0.149 s
**Generation time:** 9.224 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 4, "score": 0.5631, "vector_score": 0.5433, "lexical_score": 0.6, "snippet": "fferent propositions which were further used as the\ntraining and testing. Two features were extracted from each\nimages and tested on the two classifiers SVM and k -NN.\nLinear and polynomial kernel function s were applied in case\nof SVM and k -NN were tested with 1, 3, 5 and 7 as different\nvalues for k [9].\nThe dataset consist of 7000 images of same size were\ncollected from 20 writers of different "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.5343, "vector_score": 0.4989, "lexical_score": 0.6, "snippet": "are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap images of the characters and then Euclidean\ndistance between the testing point and ref"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.5148, "vector_score": 0.4689, "lexical_score": 0.6, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.4673, "vector_score": 0.5035, "lexical_score": 0.4, "snippet": "classifiers were tested for the\nrecognition of Gurmukhi characters from documents. In first,\n128 features comprised of distance profiles. Second feature\nset was different histogram projection of size 190 and in last\nzonal density and background directional distribution forming\n144 features. These were applied on three classifiers names\nSVM, PNN and k -NN. The SVM was tested with radial basis\nkerne"}]`

**Generated answer:**

Based on the context provided, the evaluation metric used was accuracy. Specifically, the methodology achieved 94.29% accuracy in Gurmukhi script classification using Gabor based features. Additionally, another system achieved 96.6% accuracy, and a third approach using a combination of horizontal and vertical projection features with k-NN and SVM classifiers achieved 94.12% accuracy.

- manual_score: 1
- manual_notes: Accuracy is a reasonable metric from the reported percentages, but the answer adds unsupported specific details.

#### Question 8

**Question:** What does the main results table compare?

**Retrieval backend:** chroma
**Retrieval time:** 0.169 s
**Generation time:** 9.438 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 10, "score": 0.4612, "vector_score": 0.4788, "lexical_score": 0.4286, "snippet": "ween classes is done by\nconstructing a hyper plane  [15]. The main goal is to find an\noptimal hyper plane  which expects to generalize the\ncomparison to th e others. The optimal hyper plane  is one\nwhich maximizes a measure of the “margin” between such\nclasses. The unknown data sample is then classified by the\nSVM according to the decision boundaries defined by these\nhyper planes . Hyper planes  w"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 9, "score": 0.46, "vector_score": 0.4769, "lexical_score": 0.4286, "snippet": "s the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x a"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 12, "score": 0.404, "vector_score": 0.3907, "lexical_score": 0.4286, "snippet": "45 different classes of\ncharacters including 35 alphabets and ten  numeric characters.\nA multiclass SVM classifier tool LIBSVM (A Library for\nSupport Vector Machines) has been used in this study.\nThe performance of classification on LIBSVM tool is\nmeasured by considering two types of SVM namely, C -SVC\nand nu-SVC and three types of kernels namely, Gaussian RBF\n(Radial Basis Function) kernel, Linea"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.3799, "vector_score": 0.4306, "lexical_score": 0.2857, "snippet": "classifiers were tested for the\nrecognition of Gurmukhi characters from documents. In first,\n128 features comprised of distance profiles. Second feature\nset was different histogram projection of size 190 and in last\nzonal density and background directional distribution forming\n144 features. These were applied on three classifiers names\nSVM, PNN and k -NN. The SVM was tested with radial basis\nkerne"}]`

**Generated answer:**

The main results table compares the classification accuracy obtained using different types of Support Vector Machine (SVM) and kernel functions. Specifically, it compares:

1. Two types of SVM: nu-SVC and C-SVC
2. Three types of kernel functions: Gaussian RBF kernel, Linear Kernel, and Polynomial kernel

The table shows the accuracy percentages for each combination of SVM type and kernel function.

- manual_score: 2
- manual_notes: Correct and supported: the main results compare C-SVC vs nu-SVC across RBF, linear, and polynomial kernels.

#### Question 9

**Question:** What limitations or future work are mentioned?

**Retrieval backend:** chroma
**Retrieval time:** 0.24 s
**Generation time:** 11.89 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.3824, "vector_score": 0.4088, "lexical_score": 0.3333, "snippet": "are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap images of the characters and then Euclidean\ndistance between the testing point and ref"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 2, "score": 0.3809, "vector_score": 0.4065, "lexical_score": 0.3333, "snippet": "on the blocks of an\nimages. The information from each block was concatenated to\nform a single feature vector of dimensionality 2000. The\nmethod was tested on two different dataset each having 7000\nand 2000 binary images. The recognition rate of Gurmukhi\ncharacters and numerals were found  out to be 97.38% and\n99.65%. The work was also extended to find out collective\naccuracy of methodology for bot"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 6, "score": 0.3692, "vector_score": 0.3885, "lexical_score": 0.3333, "snippet": "ion . In second, characters falling in middle zone\nset were further divided into smaller sets. In last stage, special\nfeatures were employed to distinguish the characters with the\nhelp of nearest neighbor classifier.\nAs we see, most of the work is done for han dwritten character\nrecognition and very little work is done to provide an OCR\nsystem for printed character recognition. Gurmukhi language\nh"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.3117, "vector_score": 0.3898, "lexical_score": 0.1667, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}]`

**Generated answer:**

Based on the provided context, there are no explicit mentions of limitations or specific future work. The context primarily discusses the methods and results of various studies on Gurmukhi character recognition but does not detail any limitations or suggest future research directions. 

However, it does imply some challenges and areas for potential future work by mentioning:
- The difficulty in collecting large datasets for handwriting recognition.
- The need for an OCR system for printed character recognition.
- The variations in font styles due to different backgrounds and regions.

These points suggest that future work could focus on improving data collection methods, developing more robust systems for printed character recognition, and addressing the challenges posed by font style variations.

- manual_score: 1
- manual_notes: Fairly cautious in saying no explicit limitation/future work is shown, but it then speculates beyond the snippets.

#### Question 10

**Question:** At a high level, how does the method work based on both the text and the figures?

**Retrieval backend:** chroma
**Retrieval time:** 0.304 s
**Generation time:** 24.503 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.5144, "vector_score": 0.5221, "lexical_score": 0.5, "snippet": "is observed that highest accuracy of\n97.87% has been achieved from RBF kernel of nu-SVC type\nof SVM.\n5. CONCLUSION\nIn this paper printed character recognition system for\nGurumukhi is proposed. H ierarchical centroid method is used\nfor feature extraction  which does not require fixed size as\ncompared to existing work. The obtained feature vector is\nthen learned for classification using Support Vect"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 8, "score": 0.5109, "vector_score": 0.5616, "lexical_score": 0.4167, "snippet": "extraction from printed character images of Hebrew\nlanguage. The method is based on recursive subdivisions of\ninput binary image by measuring  centroids at each division\nand outputs a fixed length features vector. Further, feature\nvector are normalized according the size of the input image.\nTherefore the size of images does not affect the final feature\nset. The method is a two -step procedure in w"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 4, "score": 0.4799, "vector_score": 0.5588, "lexical_score": 0.3333, "snippet": "fferent propositions which were further used as the\ntraining and testing. Two features were extracted from each\nimages and tested on the two classifiers SVM and k -NN.\nLinear and polynomial kernel function s were applied in case\nof SVM and k -NN were tested with 1, 3, 5 and 7 as different\nvalues for k [9].\nThe dataset consist of 7000 images of same size were\ncollected from 20 writers of different "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.4731, "vector_score": 0.5484, "lexical_score": 0.3333, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}]`

**Generated answer:**

Based on the provided context, the method for printed character recognition of Gurumukhi script works as follows:

1. **Feature Extraction**:
   - **Hierarchical Centroid Method**: The text mentions that a hierarchical centroid method is used for feature extraction. This method does not require a fixed size, unlike some existing methods. It recursively subdivides the input binary image by measuring centroids at each division. The feature vector is normalized according to the size of the input image, ensuring that the size of the images does not affect the final feature set. The length of the feature vector is given by \(2^d - 1\), where \(d\) is the recursive depth or number of divisions.

2. **Classification**:
   - **Support Vector Machine (SVM)**: The extracted feature vectors are then used to train a Support Vector Machine (SVM) classifier. The study tested different combinations of SVM types and kernels on a 10-fold cross-validation procedure. The highest accuracy of 97.87% was achieved using the nu-SVC type with the RBF kernel.

3. **Dataset and Preprocessing**:
   - The dataset consists of 7000 images of different font sizes and types, collected from 20 writers of varying age groups. Preprocessing includes converting the images to binary using Otsu's method, applying a median filter, and performing morphological operations. Iterative segmentation is used, and Gabor-based features (GABM and GABN) are used for training the SVM classifier.

4. **Performance**:
   - The highest accuracy of 97.87% was achieved, indicating the effectiveness of the method. The study suggests that this work can be extended to handwritten Gurumukhi character recognition due to its high performance.

This method leverages the hierarchical centroid approach for feature extraction and employs SVM for classification, achieving high accuracy in recognizing Gurumukhi characters from printed documents.

- manual_score: 1
- manual_notes: Core method (hierarchical centroid/recursive divisions + SVM) is supported, but much of the preprocessing detail is unsupported.

#### Question 11

**Question:** What is the central topic of the document?

**Retrieval backend:** chroma
**Retrieval time:** 0.291 s
**Generation time:** 8.488 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.3472, "vector_score": 0.4264, "lexical_score": 0.2, "snippet": "is observed that highest accuracy of\n97.87% has been achieved from RBF kernel of nu-SVC type\nof SVM.\n5. CONCLUSION\nIn this paper printed character recognition system for\nGurumukhi is proposed. H ierarchical centroid method is used\nfor feature extraction  which does not require fixed size as\ncompared to existing work. The obtained feature vector is\nthen learned for classification using Support Vect"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 7, "score": 0.329, "vector_score": 0.3984, "lexical_score": 0.2, "snippet": "total 35 characters\nin Punjabi and 10  numerals. So a dataset of 3915 images is\ncreated in the proposed study. Size of images varies from\n20*21 pixels to 40*41 pixels with a bit depth of 1. The sample\nimages of font styles used in our dataset are shown in Figure\n3.\nStyle name Fonts sample\nAdami\nRangdar\nAdhiapak\nFig. 3 Sample Font Styles of our Dataset\n[Página 3]\nInternational Journal of Computer A"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 10, "score": 0.3288, "vector_score": 0.3982, "lexical_score": 0.2, "snippet": "ween classes is done by\nconstructing a hyper plane  [15]. The main goal is to find an\noptimal hyper plane  which expects to generalize the\ncomparison to th e others. The optimal hyper plane  is one\nwhich maximizes a measure of the “margin” between such\nclasses. The unknown data sample is then classified by the\nSVM according to the decision boundaries defined by these\nhyper planes . Hyper planes  w"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.3245, "vector_score": 0.3916, "lexical_score": 0.2, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}]`

**Generated answer:**

The central topic of the document is the proposed printed character recognition system for Gurumukhi, focusing on the use of a hierarchical centroid method for feature extraction and Support Vector Machine (SVM) with a Radial Basis Function (RBF) kernel for classification. The document reports achieving a highest accuracy of 97.87% on a dataset of 3915 images created using different font sizes and types.

- manual_score: 2
- manual_notes: Correct and grounded: the paper is about printed Gurumukhi character recognition using hierarchical centroid features and SVM.

#### Question 12

**Question:** What are the 3 most important sections or takeaways?

**Retrieval backend:** chroma
**Retrieval time:** 0.151 s
**Generation time:** 20.821 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.3662, "vector_score": 0.4095, "lexical_score": 0.2857, "snippet": "are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap images of the characters and then Euclidean\ndistance between the testing point and ref"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 9, "score": 0.3597, "vector_score": 0.3995, "lexical_score": 0.2857, "snippet": "s the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x a"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.3595, "vector_score": 0.3992, "lexical_score": 0.2857, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 2, "score": 0.3532, "vector_score": 0.3896, "lexical_score": 0.2857, "snippet": "on the blocks of an\nimages. The information from each block was concatenated to\nform a single feature vector of dimensionality 2000. The\nmethod was tested on two different dataset each having 7000\nand 2000 binary images. The recognition rate of Gurmukhi\ncharacters and numerals were found  out to be 97.38% and\n99.65%. The work was also extended to find out collective\naccuracy of methodology for bot"}]`

**Generated answer:**

Based on the provided context, here are three important sections or takeaways:

1. **Feature Extraction and Classification Methods**:
   - **Skelton-Based Features**: Munish et al. used skeleton-based features along with diagonal and transition features for Gurmukhi character recognition. They employed k-NN classifiers and achieved an accuracy of 94.12% with a dataset of 3500 images.
   - **Combination of Projections and Classifiers**: Another method combined horizontal and vertical projection features with k-NN and SVM classifiers. This approach used 3500 samples from 10 different people and achieved good results.

2. **Feature Vector Construction**:
   - **Transposed Image Features**: For constructing the final feature vector, features were calculated for both the original and transposed images. This balanced the output vector and improved the classification accuracy.
   - **Depth-Based Divisions**: The input image was divided at different depth levels along x and y coordinates, and the final feature vector was the concatenation of both the original and transposed image vectors.

3. **Recognition Rates and Performance**:
   - **High Recognition Rates**: Various studies reported high recognition rates, such as 97.38% for Gurmukhi characters and 99.65% for numerals.
   - **Processing Speed**: One method achieved a recognition rate of 96.6% and processed 175 characters per second.

These sections highlight the key methods, features, and performance metrics used in Gurmukhi character recognition.

- manual_score: 1
- manual_notes: Grounded in snippets but mostly summarizes prior work/noisy retrieval instead of the paper’s own main takeaways.

#### Question 13

**Question:** Does the document contain tables? What do they show?

**Retrieval backend:** chroma
**Retrieval time:** 0.307 s
**Generation time:** 13.837 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 7, "score": 0.3827, "vector_score": 0.4542, "lexical_score": 0.25, "snippet": "total 35 characters\nin Punjabi and 10  numerals. So a dataset of 3915 images is\ncreated in the proposed study. Size of images varies from\n20*21 pixels to 40*41 pixels with a bit depth of 1. The sample\nimages of font styles used in our dataset are shown in Figure\n3.\nStyle name Fonts sample\nAdami\nRangdar\nAdhiapak\nFig. 3 Sample Font Styles of our Dataset\n[Página 3]\nInternational Journal of Computer A"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.3445, "vector_score": 0.4627, "lexical_score": 0.125, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 9, "score": 0.3303, "vector_score": 0.4409, "lexical_score": 0.125, "snippet": "s the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x a"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 10, "score": 0.3255, "vector_score": 0.4334, "lexical_score": 0.125, "snippet": "ween classes is done by\nconstructing a hyper plane  [15]. The main goal is to find an\noptimal hyper plane  which expects to generalize the\ncomparison to th e others. The optimal hyper plane  is one\nwhich maximizes a measure of the “margin” between such\nclasses. The unknown data sample is then classified by the\nSVM according to the decision boundaries defined by these\nhyper planes . Hyper planes  w"}]`

**Generated answer:**

The provided context does not contain any explicit tables. However, it does describe some visual elements such as Figure 3, which shows "Sample Font Styles of our Dataset," and Figure 4, which illustrates "Divisions of s at different depth levels along x and y coordinates." These figures are likely to be visual representations rather than tables. The text mentions these figures but does not provide their具体内容如下：
文档中没有明确包含表格。然而，它确实描述了一些视觉元素，如图3，显示了“我们的数据集中字体样式的样本”，以及图4，展示了“不同深度级别沿x和y坐标的s的划分”。这些图像是视觉表示，而不是表格。文本提到了这些图像，但没有提供它们的具体内容。根据提供的上下文，无法确定这些图像是什么类型的视觉表示。

- manual_score: 1
- manual_notes: Reasonable from the snippets that no explicit tables are shown, but the response is noisy and includes irrelevant Chinese text.

#### Question 14

**Question:** Does the document contain figures or diagrams? What do they show?

**Retrieval backend:** chroma
**Retrieval time:** 0.308 s
**Generation time:** 6.417 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 7, "score": 0.3785, "vector_score": 0.4626, "lexical_score": 0.2222, "snippet": "total 35 characters\nin Punjabi and 10  numerals. So a dataset of 3915 images is\ncreated in the proposed study. Size of images varies from\n20*21 pixels to 40*41 pixels with a bit depth of 1. The sample\nimages of font styles used in our dataset are shown in Figure\n3.\nStyle name Fonts sample\nAdami\nRangdar\nAdhiapak\nFig. 3 Sample Font Styles of our Dataset\n[Página 3]\nInternational Journal of Computer A"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.3583, "vector_score": 0.4316, "lexical_score": 0.2222, "snippet": "is observed that highest accuracy of\n97.87% has been achieved from RBF kernel of nu-SVC type\nof SVM.\n5. CONCLUSION\nIn this paper printed character recognition system for\nGurumukhi is proposed. H ierarchical centroid method is used\nfor feature extraction  which does not require fixed size as\ncompared to existing work. The obtained feature vector is\nthen learned for classification using Support Vect"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.3542, "vector_score": 0.4851, "lexical_score": 0.1111, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.3326, "vector_score": 0.4518, "lexical_score": 0.1111, "snippet": "classifiers were tested for the\nrecognition of Gurmukhi characters from documents. In first,\n128 features comprised of distance profiles. Second feature\nset was different histogram projection of size 190 and in last\nzonal density and background directional distribution forming\n144 features. These were applied on three classifiers names\nSVM, PNN and k -NN. The SVM was tested with radial basis\nkerne"}]`

**Generated answer:**

Yes, the document contains figures. Specifically, Figure 3 shows sample font styles of the dataset used in the study. These include font styles named Adami, Rangdar, and Adhiapak.

- manual_score: 1
- manual_notes: Correctly identifies Figure 3 and its sample font styles, but it is incomplete for the broader question about figures/diagrams.

#### Question 15

**Question:** What is one important piece of information from the middle of the document?

**Retrieval backend:** chroma
**Retrieval time:** 0.145 s
**Generation time:** 8.823 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 13, "score": 0.3982, "vector_score": 0.4332, "lexical_score": 0.3333, "snippet": "is observed that highest accuracy of\n97.87% has been achieved from RBF kernel of nu-SVC type\nof SVM.\n5. CONCLUSION\nIn this paper printed character recognition system for\nGurumukhi is proposed. H ierarchical centroid method is used\nfor feature extraction  which does not require fixed size as\ncompared to existing work. The obtained feature vector is\nthen learned for classification using Support Vect"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 1, "score": 0.397, "vector_score": 0.4313, "lexical_score": 0.3333, "snippet": "[Página 2]\nInternational Journal of Computer Applications (0975 – 8887)\nVolume 149 – No.3, September 2016\n25\nrecognition. Some of these studies are briefly reviewed as\nfollows:\nThe zoning mechanism is used for the feature extraction\nwhich is used to train support vecto r machine (SVM). This\npaper present a technique for the recognition Gurmukhi\ncharacters which works in two phases: In first phase "}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.3965, "vector_score": 0.4306, "lexical_score": 0.3333, "snippet": "are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap images of the characters and then Euclidean\ndistance between the testing point and ref"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 2, "score": 0.3872, "vector_score": 0.4162, "lexical_score": 0.3333, "snippet": "on the blocks of an\nimages. The information from each block was concatenated to\nform a single feature vector of dimensionality 2000. The\nmethod was tested on two different dataset each having 7000\nand 2000 binary images. The recognition rate of Gurmukhi\ncharacters and numerals were found  out to be 97.38% and\n99.65%. The work was also extended to find out collective\naccuracy of methodology for bot"}]`

**Generated answer:**

One important piece of information from the middle of the document is that the highest accuracy of 97.87% was achieved using the nu-SVC type of SVM with the RBF kernel. This result comes from the hierarchical centroid method used for feature extraction in a printed character recognition system for Gurumukhi.

- manual_score: 1
- manual_notes: The 97.87% result is supported, but it comes from the conclusion rather than the middle of the document; retrieval seems off.

#### Question 16

**Question:** What is one limitation, note, or important observation mentioned near the end?

**Retrieval backend:** chroma
**Retrieval time:** 0.168 s
**Generation time:** 9.55 s
**Top sources:** `[{"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 9, "score": 0.3213, "vector_score": 0.3866, "lexical_score": 0.2, "snippet": "s the recursive depth or\ndivisions. But it produces subdivisions along one axis twice as\ncompare to other. Therefore, in order to balance output vector,\nfeatures are also cal culated along transposed image.\nOriginal Character Transposed Character\nDepth 1 Depth 2 Depth 3 Depth 1 Depth 2 Depth 3\nDepth 4 Depth 5 Depth 6 Depth 4 Depth 5 Depth 6\nFig. 4 Divisions of s at different depth levels along x a"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 5, "score": 0.321, "vector_score": 0.3861, "lexical_score": 0.2, "snippet": "classifiers were tested for the\nrecognition of Gurmukhi characters from documents. In first,\n128 features comprised of distance profiles. Second feature\nset was different histogram projection of size 190 and in last\nzonal density and background directional distribution forming\n144 features. These were applied on three classifiers names\nSVM, PNN and k -NN. The SVM was tested with radial basis\nkerne"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 3, "score": 0.3012, "vector_score": 0.4096, "lexical_score": 0.1, "snippet": "are found out to be\n96.6% and 175 characters per second [3].\nMunish et. al presented a work on recognition of Gurmukhi\ncharacters by employing k -NN classifiers. First Skelton of\neach character is prepared in order to extract its feature\ninformation. Diagonal and transition features were calculated\non the bitmap images of the characters and then Euclidean\ndistance between the testing point and ref"}, {"source": "kaur-2016-ijca-911367.pdf", "document_id": "b88d96e8424a2a9e80ca8761dc5b6e8b34ecab01738a70459e5613d920184494", "file_type": "pdf", "chunk_id": 2, "score": 0.294, "vector_score": 0.3985, "lexical_score": 0.1, "snippet": "on the blocks of an\nimages. The information from each block was concatenated to\nform a single feature vector of dimensionality 2000. The\nmethod was tested on two different dataset each having 7000\nand 2000 binary images. The recognition rate of Gurmukhi\ncharacters and numerals were found  out to be 97.38% and\n99.65%. The work was also extended to find out collective\naccuracy of methodology for bot"}]`

**Generated answer:**

One limitation mentioned near the end is the challenge in recognizing Gurmukhi script, particularly for machine-printed characters. The text notes that this faces major problems such as:

- Unique characteristics of the script like connectivity of characters on the headline
- A large number of similar characters
- Two or more characters in a word having intersecting minimum bounding rectangles

These issues make recognition difficult, especially when sentences need to be segmented into characters.

- manual_score: 0
- manual_notes: Unsupported and off-target: it cites general script challenges not shown in the Top sources and not specifically near the end.
