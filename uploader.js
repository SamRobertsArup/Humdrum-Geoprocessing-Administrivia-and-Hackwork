
export async function getUpload(props) {
	//
	// pass event from <input onChange={handleFileSelected} ref={r => fileInput = r}  type="file" multiple/> <button onClick={() => fileInput.click()}/>
	// where handleFileSelect is an async function containing await getUpload
	//
    console.log(props.target.files)

    const uploadFile = async (file) => {
        return new Promise((resolve, reject) => {
          let fileReader = new FileReader();
          fileReader.onload = () => {
            resolve(fileReader.result);
          };
          fileReader.onerror = reject; // notify user with reject
          fileReader.readAsArrayBuffer(file);
        });
    }

    const files = Object.keys(props.target.files).map(i=> props.target.files[i])

    const uploaded = await Promise.all(files.map(async (file) => {
      const fileObj = {};
      const fileContents = await uploadFile(file);
      fileObj['content'] = fileContents
      fileObj['name'] = file.name
      return fileObj
    }));
    
    // corrects key: value to uploaded[fileextension]: {contents,  filename}
    Object.keys(uploaded).map(i=> {
        Object.defineProperty(uploaded, uploaded[i].name.split(".")[1], Object.getOwnPropertyDescriptor(uploaded, i))
        delete uploaded[i]; 
      }
    )

    return uploaded
}


export const ab2str = (buf) => {
  const chunk = 100000
  var str, i, j, temporary 
  if (buf.byteLength>chunk) {
    for (i = 0, j = buf.byteLength; i < j; i += chunk) {
      temporary = buf.slice(i, i + chunk);
      str += String.fromCharCode.apply(null, new Uint8Array(temporary))
    }
  } else {
    str = String.fromCharCode.apply(null, new Uint8Array(buf)); // error handling when file too big (> 150kb)
  }
  return str  
}

export function csv2arr( strData, strDelimiter ){
  // Check to see if the delimiter is defined. If not,
  // then default to comma.
  strDelimiter = (strDelimiter || ",");

  // Create a regular expression to parse the CSV values.
  var objPattern = new RegExp(
    (
      // Delimiters.
      "(\\" + strDelimiter + "|\\r?\\n|\\r|^)" +

      // Quoted fields.
      "(?:\"([^\"]*(?:\"\"[^\"]*)*)\"|" +

      // Standard fields.
      "([^\"\\" + strDelimiter + "\\r\\n]*))"
    ),
    "gi"
    );


  // Create an array to hold our data. Give the array
  // a default empty first row.
  var arrData = [[]];

  // Create an array to hold our individual pattern
  // matching groups.
  var arrMatches = null;


  // Keep looping over the regular expression matches
  // until we can no longer find a match.
  while (arrMatches = objPattern.exec( strData )){

    // Get the delimiter that was found.
    var strMatchedDelimiter = arrMatches[ 1 ];

    // Check to see if the given delimiter has a length
    // (is not the start of string) and if it matches
    // field delimiter. If id does not, then we know
    // that this delimiter is a row delimiter.
    if (
      strMatchedDelimiter.length &&
      (strMatchedDelimiter != strDelimiter)
      ){

      // Since we have reached a new row of data,
      // add an empty row to our data array.
      arrData.push( [] );

    }


    // Now that we have our delimiter out of the way,
    // let's check to see which kind of value we
    // captured (quoted or unquoted).
    if (arrMatches[ 2 ]){

      // We found a quoted value. When we capture
      // this value, unescape any double quotes.
      var strMatchedValue = arrMatches[ 2 ].replace(
        new RegExp( "\"\"", "g" ),
        "\""
        );

    } else {

      // We found a non-quoted value.
      var strMatchedValue = arrMatches[ 3 ];

    }


    // Now that we have our value string, let's add
    // it to the data array.
    arrData[ arrData.length - 1 ].push( strMatchedValue );
  }

  // Return the parsed data.
  return( arrData );
}