/* Isolate the 2014 reader from saved modern homebrew/settings, preserving both. */
(() => {
  const storage=globalThis.StorageUtil;
  if(!storage||storage._campaign2014Storage)return;
  const prefix='campaign-desk:reference-2014:';
  const getSync=storage._getSyncStorage.bind(storage),getAsync=storage._getAsyncStorage.bind(storage);
  storage._getSyncStorage=()=>{
    const backing=getSync();
    return {isSyncFake:backing.isSyncFake,getItem:key=>backing.getItem(prefix+key),
      setItem:(key,value)=>backing.setItem(prefix+key,value),removeItem:key=>backing.removeItem(prefix+key)};
  };
  storage._getAsyncStorage=async()=>{
    const backing=await getAsync();
    return {pIsAsyncFake:backing.pIsAsyncFake,getItem:key=>backing.getItem(prefix+key),
      setItem:(key,value)=>backing.setItem(prefix+key,value),removeItem:key=>backing.removeItem(prefix+key)};
  };
  storage._campaign2014Storage=true;
})();
