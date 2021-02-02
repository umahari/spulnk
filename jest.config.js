module.exports = {
  testMatch: [
    '**/*.spec.js',
  ],
  collectCoverage: true,
  collectCoverageFrom: ['**/*.js'],
  
  reporters: [
    "default",
    [ "jest-junit", 
     {
      outputDirectory: '.',
      outputName: 'jest-junit.xml',
    } ]
  ]
};
