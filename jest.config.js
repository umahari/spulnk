module.exports = {
  testMatch: [
    '**/*.spec.js',
  ],
  collectCoverage: true,
  reporters: [
    "default",
    [ "jest-junit", 
     {
      outputDirectory: '.',
      outputName: 'jest-junit.xml',
    } ]
  ]
};
