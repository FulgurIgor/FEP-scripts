git clone https://github.com/deGrootLab/pmx.git -b develop
cp 0001-Fix-for-old-git.patch pmx
cd pmx
git apply 0001-Fix-for-old-git.patch pmx
python setup.py install --user
cd ..
