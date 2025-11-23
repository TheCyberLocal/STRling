local strling = require("src.strling")

describe("STRling", function()
  it("exists", function()
    assert.is_not_nil(strling)
  end)
  
  it("has a compile function", function()
    assert.is_not_nil(strling.compile)
  end)
end)
