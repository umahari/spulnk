module.exports = {
  testMatch: [
    '**/*.spec.js',
  ],
  reporters: [
    "default",
    [ "jest-junit", 
     {
      outputDirectory: '.',
      outputName: 'jest-junit.xml',
    } ]
  ]
};
