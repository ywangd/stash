echo StaSh is trying to selfupdate ...
wget https://github.com/ywangd/stash/archive/$SELFUPDATE_BRANCH.zip -o $STASH_ROOT/stash.zip
echo Extracting to $STASH_ROOT
unzip $STASH_ROOT/stash.zip -d $STASH_ROOT
rm $STASH_ROOT/stash.zip
rm -f $STASH_ROOT/dummyui.py
rm -f $STASH_ROOT/dummyconsole.py
rm -f $STASH_ROOT/testing.py
rm -rf $STASH_ROOT/tests
echo Done
