module.exports = {
  testMatch: [
    '**/*.spec.js',
  ],
  collectCoverage: true,
  collectCoverageFrom: ['**/*.js'],
  coveragePathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/lib/',
    '<rootDir>/build/',
    '<rootDir>/dist/'
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
