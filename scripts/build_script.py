import os
import nltk
from nltk.corpus import wordnet
from paddleocr import PaddleOCR

print("running build script")
# if the paddleOCR models are missing download them
if not os.path.exists('/root/.paddleocr'):
    print("Downloading PaddleOCR models")
    PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
else:
    print("PaddleOCR models have been already downloaded")


# Check if wordnet is already available
try:
    nltk.data.find('corpora/wordnet.zip')
    print("wordnet is already available")
# if not, download it
except LookupError:
    print("wordnet was not found")
    nltk.download('wordnet', quiet=True)
    print("wordnet download complete")

# load wordnet synsets into memory
_ = wordnet.synsets('dog')

