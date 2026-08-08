#include <TBranch.h>
#include <TFile.h>
#include <TLeaf.h>
#include <TObjArray.h>
#include <TTree.h>

#include <cmath>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

namespace {

bool SameDoubleBits(const double left, const double right) {
  return std::memcmp(&left, &right, sizeof(double)) == 0;
}

bool IsStringBranch(const TBranch& branch) {
  const std::string className = branch.GetClassName();
  return className == "string" || className == "std::string";
}

bool CompareTree(TTree& left, TTree& right, int& differences) {
  const std::string treeName = left.GetName();
  if (left.GetEntries() != right.GetEntries()) {
    std::cerr << "[DIFF] " << treeName << ": número de entradas\n";
    ++differences;
    return false;
  }

  TObjArray* leftBranches = left.GetListOfBranches();
  TObjArray* rightBranches = right.GetListOfBranches();
  if (leftBranches->GetEntries() != rightBranches->GetEntries()) {
    std::cerr << "[DIFF] " << treeName << ": número de branches\n";
    ++differences;
    return false;
  }

  struct StringBranch {
    std::string name;
    std::string* leftValue = nullptr;
    std::string* rightValue = nullptr;
  };
  std::vector<StringBranch> strings;

  for (int index = 0; index < leftBranches->GetEntries(); ++index) {
    auto* leftBranch = static_cast<TBranch*>(leftBranches->At(index));
    auto* rightBranch = right.GetBranch(leftBranch->GetName());
    if (!rightBranch) {
      std::cerr << "[DIFF] " << treeName << ": branch ausente: "
                << leftBranch->GetName() << '\n';
      ++differences;
      return false;
    }
    if (IsStringBranch(*leftBranch)) {
      strings.push_back({leftBranch->GetName(), nullptr, nullptr});
    }
  }

  for (auto& branch : strings) {
    left.SetBranchAddress(branch.name.c_str(), &branch.leftValue);
    right.SetBranchAddress(branch.name.c_str(), &branch.rightValue);
  }

  for (Long64_t entry = 0; entry < left.GetEntries(); ++entry) {
    left.GetEntry(entry);
    right.GetEntry(entry);

    for (int index = 0; index < leftBranches->GetEntries(); ++index) {
      auto* leftBranch = static_cast<TBranch*>(leftBranches->At(index));
      auto* rightBranch = right.GetBranch(leftBranch->GetName());
      if (IsStringBranch(*leftBranch)) {
        continue;
      }

      TLeaf* leftLeaf = leftBranch->GetLeaf(leftBranch->GetName());
      TLeaf* rightLeaf = rightBranch->GetLeaf(rightBranch->GetName());
      if (!leftLeaf || !rightLeaf ||
          std::string(leftLeaf->GetTypeName()) != rightLeaf->GetTypeName() ||
          leftLeaf->GetLen() != rightLeaf->GetLen()) {
        std::cerr << "[DIFF] " << treeName << '.' << leftBranch->GetName()
                  << ": tipo ou dimensão\n";
        ++differences;
        return false;
      }
      for (int element = 0; element < leftLeaf->GetLen(); ++element) {
        if (!SameDoubleBits(leftLeaf->GetValue(element),
                            rightLeaf->GetValue(element))) {
          std::cerr << "[DIFF] " << treeName << '.' << leftBranch->GetName()
                    << " na entrada " << entry << '\n';
          ++differences;
          return false;
        }
      }
    }

    for (const auto& branch : strings) {
      if (!branch.leftValue || !branch.rightValue ||
          *branch.leftValue != *branch.rightValue) {
        std::cerr << "[DIFF] " << treeName << '.' << branch.name
                  << " na entrada " << entry << '\n';
        ++differences;
        return false;
      }
    }
  }

  left.ResetBranchAddresses();
  right.ResetBranchAddresses();
  return true;
}

}  // namespace

void compare_root(const char* leftFilename, const char* rightFilename) {
  TFile leftFile(leftFilename, "READ");
  TFile rightFile(rightFilename, "READ");
  int differences = 0;

  if (leftFile.IsZombie() || rightFile.IsZombie()) {
    std::cerr << "[DIFF] não foi possível abrir os dois arquivos\n";
    std::cout << "COMPARE_RESULT=FAIL differences=1\n";
    return;
  }

  for (const char* name : {"events", "hits", "generator", "metadata"}) {
    auto* leftTree = leftFile.Get<TTree>(name);
    auto* rightTree = rightFile.Get<TTree>(name);
    if (!leftTree || !rightTree) {
      std::cerr << "[DIFF] TTree ausente: " << name << '\n';
      ++differences;
      continue;
    }
    CompareTree(*leftTree, *rightTree, differences);
  }

  if (differences == 0) {
    std::cout << "COMPARE_RESULT=PASS\n";
  } else {
    std::cout << "COMPARE_RESULT=FAIL differences=" << differences << '\n';
  }
}
