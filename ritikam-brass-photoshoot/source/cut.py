import sys
from rembg import remove, new_session
from PIL import Image
o=remove(Image.open(sys.argv[1]).convert('RGB'),session=new_session('birefnet-general'))
o.save(sys.argv[2]);print(sys.argv[2],o.size,o.getbbox())
