const request = require('supertest');
const expect = require('chai').expect;

describe('Greencheck API', () => {
  it('Has the correct URL property', () => {
    request('https://django:8000')
      .get('/greencheck/climateaction.tech')
      .expect(200)
      .expect('Content-Type', 'application/json')
      .expect(function(res) {
        if (!res.body.hasOwnProperty('url')) throw new Error("Expected 'url' key!");
      })
      .end(function(err, res){
        if (err) throw err;
      })
  });
});