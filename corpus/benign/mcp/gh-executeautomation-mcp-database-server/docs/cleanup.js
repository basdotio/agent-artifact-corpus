const fs = require('fs');
const path = require('path');

const directoriesToRemove = [
  './docs/local-setup',
  './docs/playwright-web',
  './docs/playwright-api',
  './docs/testing-videos',
];

// Function to delete a directory recursively
function deleteFolderRecursive(directoryPath) {
  if (fs.existsSync(directoryPath)) {
    fs.readdirSync(directoryPath).forEach((file) => {
      const curPath = path.join(directoryPath, file);
      if (fs.lstatSync(curPath).isDirectory()) {
        deleteFolderRecursive(curPath);
      } else {
        fs.unlinkSync(curPath);
      }
    });
    fs.rmdirSync(directoryPath);
    console.log(`Removed directory: ${directoryPath}`);
  }
}

// Delete each directory
directoriesToRemove.forEach((directory) => {
  try {
    deleteFolderRecursive(directory);
  } catch (error) {
    console.error(`Error deleting ${directory}:`, error);
  }
});

console.log('Cleanup completed!'); 