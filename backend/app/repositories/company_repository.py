from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from app.models.orm import CompanyORM

class CompanyRepository:
    def __init__(self, session: Session):
        self.session = session

    def _extract_domain(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        try:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain if domain else None
        except Exception:
            return None

    def get_by_id(self, company_id: str) -> Optional[Dict[str, Any]]:
        comp = self.session.query(CompanyORM).filter(CompanyORM.id == company_id).first()
        if not comp:
            return None
        return self._to_dict(comp)

    def get_by_career_url(self, career_url: str) -> Optional[Dict[str, Any]]:
        comp = self.session.query(CompanyORM).filter(CompanyORM.career_url == career_url).first()
        if not comp:
            return None
        return self._to_dict(comp)

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        comp = self.session.query(CompanyORM).filter(CompanyORM.name.ilike(name)).first()
        if not comp:
            return None
        return self._to_dict(comp)

    def lookup_or_create(self, name: str, career_url: Optional[str] = None, website: Optional[str] = None, industry: Optional[str] = None, logo_url: Optional[str] = None) -> Dict[str, Any]:
        comp = None
        if career_url:
            comp = self.session.query(CompanyORM).filter(CompanyORM.career_url == career_url).first()
        if not comp and website:
            domain = self._extract_domain(website)
            if domain:
                comps = self.session.query(CompanyORM).all()
                for c in comps:
                    if self._extract_domain(c.website) == domain or self._extract_domain(c.career_url) == domain:
                        comp = c
                        break
        if not comp:
            comp = self.session.query(CompanyORM).filter(CompanyORM.name.ilike(name)).first()

        if comp:
            if not comp.website and website:
                comp.website = website
            if not comp.industry and industry:
                comp.industry = industry
            if not comp.logo_url and logo_url:
                comp.logo_url = logo_url
            if not comp.career_url and career_url:
                comp.career_url = career_url
            self.session.flush()
            return self._to_dict(comp)
        else:
            comp = CompanyORM(name=name, career_url=career_url, website=website, industry=industry, logo_url=logo_url)
            self.session.add(comp)
            self.session.flush()
            return self._to_dict(comp)

    def _to_dict(self, comp: CompanyORM) -> Dict[str, Any]:
        return {
            "id": comp.id,
            "name": comp.name,
            "website": comp.website,
            "industry": comp.industry,
            "logo_url": comp.logo_url,
            "career_url": comp.career_url,
            "created_at": comp.created_at
        }
